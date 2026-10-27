from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.modules.audit.service import record_audit
from app.modules.auth.models import OrganizationMembership, User
from app.modules.marketplace.models import Product
from app.modules.orders.models import Cart, CartItem, Order, OrderItem
from app.modules.orders.schemas import (
    CartItemInput,
    CartResponse,
    MerchantOrderResponse,
    OrderItemResponse,
    OrderResponse,
)

router = APIRouter()


def get_or_create_cart(user_id: str, db: Session) -> Cart:
    cart = db.scalar(select(Cart).options(selectinload(Cart.items)).where(Cart.customer_user_id == user_id))
    if cart is None:
        cart = Cart(customer_user_id=user_id)
        db.add(cart)
        db.commit()
        cart = db.scalar(select(Cart).options(selectinload(Cart.items)).where(Cart.customer_user_id == user_id))
    return cart


def cart_response(cart: Cart, db: Session) -> CartResponse:
    result = []
    for item in cart.items:
        product = db.get(Product, item.product_id)
        if product is not None:
            result.append({"product_id": product.id, "product_title": product.title, "quantity": item.quantity, "unit_price_minor": product.price_minor, "currency": product.currency, "available_stock": product.stock_quantity})
    return CartResponse(items=result)


@router.get("/cart", response_model=CartResponse)
def get_cart(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return cart_response(get_or_create_cart(user.id, db), db)


@router.put("/cart/items", response_model=CartResponse)
def set_cart_item(payload: CartItemInput, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    product = db.scalar(select(Product).where(Product.id == payload.product_id, Product.published.is_(True)))
    if product is None:
        raise HTTPException(status_code=404, detail="Product is not available")
    if payload.quantity > product.stock_quantity:
        raise HTTPException(status_code=409, detail="Requested quantity exceeds current stock")
    cart = get_or_create_cart(user.id, db)
    item = db.scalar(select(CartItem).where(CartItem.cart_id == cart.id, CartItem.product_id == product.id).with_for_update())
    if item is None:
        db.add(CartItem(cart_id=cart.id, product_id=product.id, quantity=payload.quantity))
    else:
        item.quantity = payload.quantity
    db.commit()
    return cart_response(get_or_create_cart(user.id, db), db)


@router.delete("/cart/items/{product_id}", response_model=CartResponse)
def delete_cart_item(product_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cart = get_or_create_cart(user.id, db)
    item = db.scalar(select(CartItem).where(CartItem.cart_id == cart.id, CartItem.product_id == product_id))
    if item is not None:
        db.delete(item)
        db.commit()
    return cart_response(get_or_create_cart(user.id, db), db)


@router.post("/orders", response_model=OrderResponse, status_code=201)
def create_order(
    user: User = Depends(get_current_user),
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=8, max_length=255),
    db: Session = Depends(get_db),
):
    existing = db.scalar(select(Order).options(selectinload(Order.items)).where(Order.customer_user_id == user.id, Order.idempotency_key == idempotency_key))
    if existing is not None:
        return existing
    cart = db.scalar(select(Cart).options(selectinload(Cart.items)).where(Cart.customer_user_id == user.id).with_for_update())
    if cart is None or not cart.items:
        raise HTTPException(status_code=409, detail="Cart is empty")
    products = []
    for item in cart.items:
        product = db.scalar(select(Product).where(Product.id == item.product_id, Product.published.is_(True)).with_for_update())
        if product is None or product.stock_quantity < item.quantity:
            raise HTTPException(status_code=409, detail="A cart item is no longer available in the requested quantity")
        products.append((item, product))
    currencies = {product.currency for _, product in products}
    if len(currencies) != 1:
        raise HTTPException(status_code=409, detail="All products in a single order must use the same currency")
    subtotal = sum(item.quantity * product.price_minor for item, product in products)
    order = Order(customer_user_id=user.id, idempotency_key=idempotency_key, currency=currencies.pop(), subtotal_minor=subtotal)
    db.add(order)
    try:
        db.flush()
        for item, product in products:
            db.add(OrderItem(order_id=order.id, product_id=product.id, merchant_organization_id=product.organization_id, product_title=product.title, quantity=item.quantity, unit_price_minor=product.price_minor, currency=product.currency, line_total_minor=item.quantity * product.price_minor))
        record_audit(db, actor_user_id=user.id, action="order.created", resource_type="order", resource_id=order.id, details={"status": order.status, "subtotal_minor": order.subtotal_minor, "currency": order.currency})
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(Order).options(selectinload(Order.items)).where(Order.customer_user_id == user.id, Order.idempotency_key == idempotency_key))
        if existing is not None:
            return existing
        raise HTTPException(status_code=409, detail="Order could not be created")
    db.refresh(order)
    return db.scalar(select(Order).options(selectinload(Order.items)).where(Order.id == order.id))


@router.get("/orders", response_model=list[OrderResponse])
def list_customer_orders(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return list(db.scalars(select(Order).options(selectinload(Order.items)).where(Order.customer_user_id == user.id).order_by(Order.created_at.desc()).limit(100)))


@router.get("/merchant/orders", response_model=list[MerchantOrderResponse])
def list_merchant_orders(organization_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    membership = db.scalar(select(OrganizationMembership.role).where(OrganizationMembership.user_id == user.id, OrganizationMembership.organization_id == organization_id))
    if membership not in {"owner", "admin", "merchant_staff"}:
        raise HTTPException(status_code=404, detail="Merchant organization not found")
    orders = list(db.scalars(select(Order).join(OrderItem).options(selectinload(Order.items)).where(OrderItem.merchant_organization_id == organization_id).order_by(Order.created_at.desc()).limit(100)).unique())
    results = []
    for order in orders:
        visible_items = [item for item in order.items if item.merchant_organization_id == organization_id]
        results.append(MerchantOrderResponse(
            id=order.id,
            status=order.status,
            payment_status=order.payment_status,
            currency=order.currency,
            merchant_subtotal_minor=sum(item.line_total_minor for item in visible_items),
            created_at=order.created_at,
            items=[OrderItemResponse.model_validate(item) for item in visible_items],
        ))
    return results
