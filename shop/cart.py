from .models import Product

class Cart:
    def __init__(self, request):
        self.session = request.session
        self.cart = self.session.get("cart", {})
        if not self.cart:
            self.cart = self.session["cart"] = {}

    def add(self, product_id, quantity=1):
        product_id = str(product_id)
        if product_id in self.cart:
            self.cart[product_id] += quantity
        else:
            self.cart[product_id] = quantity
        self.save()

    def remove(self, product_id):
        product_id = str(product_id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def update(self, product_id, quantity):
        product_id = str(product_id)
        if product_id in self.cart:
            self.cart[product_id] = quantity
            self.save()

    def save(self):
        self.session["cart"] = self.cart
        self.session.modified = True

    def clear(self):
        self.session["cart"] = {}
        self.session.modified = True

    def items(self):
        products = Product.objects.filter(id__in=self.cart.keys())
        cart_items = []
        for product in products:
            pid = str(product.id)
            quantity = self.cart.get(pid, 0)
            total_price = product.price * quantity
            cart_items.append({
                "product": product,
                "quantity": quantity,
                "total_price": total_price
            })
        return cart_items

    def total(self):
        return sum(item["total_price"] for item in self.items())

    def count(self):
        return sum(self.cart.values())


# shop/cart.py

def get_cart_items(request):
    """
    Returns list of cart items with product instance, quantity, and total price.
    Cart is stored in session as {product_id: quantity}.
    """
    cart = request.session.get('cart', {})
    items = []
    for product_id, quantity in cart.items():
        try:
            product = Product.objects.get(id=product_id)
            items.append({
                'product': product,
                'quantity': quantity,
                'total_price': product.price * quantity
            })
        except Product.DoesNotExist:
            continue
    return items
