import uuid, os, json, random, string
from datetime import datetime, date
from functools import wraps
from flask import Flask, render_template, abort, request, redirect, url_for, flash, session, jsonify, send_file
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
import io

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
base_dir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__, static_folder=os.path.join(base_dir, 'static'), static_url_path='/static')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(base_dir, 'orders.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'vanilla-elegance-secret-2026')
app.config['UPLOAD_FOLDER'] = os.path.join(base_dir, 'static')
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'firaschourouk')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'firaschourouk010298')
ADMIN_WHATSAPP = os.environ.get('ADMIN_WHATSAPP', '213699615145')

db = SQLAlchemy(app)

# ══════════════════════════════════════
# MODELS
# ══════════════════════════════════════
class Product(db.Model):
    __tablename__ = 'products'
    id             = db.Column(db.Integer, primary_key=True)
    name           = db.Column(db.String(200), nullable=False)
    price          = db.Column(db.Integer, nullable=False)
    original_price = db.Column(db.Integer, nullable=True)
    image          = db.Column(db.String(200), nullable=False)
    images_json    = db.Column(db.Text, default='[]')
    stock_quantity = db.Column(db.Integer, default=10)
    category       = db.Column(db.String(100), default='Women')
    description    = db.Column(db.Text, default='')
    sizes_json     = db.Column(db.Text, default='[]')

    def get_sizes(self):
        try: return json.loads(self.sizes_json or '[]')
        except: return []

    def get_images(self):
        try: return json.loads(self.images_json or '[]')
        except: return []

    def to_dict(self):
        return {'id':self.id,'name':self.name,'price':self.price,
                'original_price':self.original_price,'image':self.image,
                'images':self.get_images(),'stock_quantity':self.stock_quantity,
                'category':self.category,'description':self.description,
                'sizes':self.get_sizes()}

class Order(db.Model):
    __tablename__ = 'orders'
    id             = db.Column(db.Integer, primary_key=True)
    tracking_code  = db.Column(db.String(12), unique=True, nullable=False)
    product_name   = db.Column(db.String(200), nullable=False)
    product_id     = db.Column(db.Integer, nullable=True)
    volume         = db.Column(db.String(50), default='')
    price          = db.Column(db.Integer, nullable=False)
    customer_first = db.Column(db.String(100), nullable=False)
    customer_last  = db.Column(db.String(100), nullable=False)
    customer_phone = db.Column(db.String(50), nullable=False)
    wilaya         = db.Column(db.String(100), nullable=False)
    delivery_type  = db.Column(db.String(50), nullable=False)
    promo_code     = db.Column(db.String(30), default='')
    discount_amount= db.Column(db.Integer, default=0)
    status         = db.Column(db.String(50), default='Pending')
    timestamp      = db.Column(db.DateTime, default=datetime.utcnow)
    completed      = db.Column(db.Boolean, default=False)

class PromoCode(db.Model):
    __tablename__ = 'promo_codes'
    id          = db.Column(db.Integer, primary_key=True)
    code        = db.Column(db.String(30), unique=True, nullable=False)
    type        = db.Column(db.String(10), default='percent')
    value       = db.Column(db.Integer, nullable=False)
    uses_left   = db.Column(db.Integer, default=-1)
    active      = db.Column(db.Boolean, default=True)

# ══════════════════════════════════════
# HELPERS
# ══════════════════════════════════════
def allowed_file(f): return '.' in f and f.rsplit('.',1)[1].lower() in ALLOWED_EXTENSIONS

def gen_tracking():
    while True:
        code = 'MD-' + ''.join(random.choices(string.ascii_uppercase+string.digits, k=8))
        if not Order.query.filter_by(tracking_code=code).first():
            return code

def login_required(f):
    @wraps(f)
    def dec(*a,**kw):
        if not session.get('admin_logged_in'):
            flash("Please log in.", "error"); return redirect(url_for('admin_login'))
        return f(*a,**kw)
    return dec

def migrate_db():
    import sqlite3
    path = os.path.join(base_dir, 'orders.db')
    if not os.path.exists(path): return
    con = sqlite3.connect(path); cur = con.cursor()
    cur.execute("PRAGMA table_info(products)")
    cols = [r[1] for r in cur.fetchall()]
    for col,typ in [('sizes_json',"TEXT DEFAULT '[]'"),('images_json',"TEXT DEFAULT '[]'"),
                    ('original_price','INTEGER'),('category',"VARCHAR(100) DEFAULT 'Women'"),
                    ('description',"TEXT DEFAULT ''")]:
        if col not in cols: cur.execute(f"ALTER TABLE products ADD COLUMN {col} {typ}")
    cur.execute("PRAGMA table_info(orders)")
    ocols = [r[1] for r in cur.fetchall()]
    for col,typ in [('tracking_code',"VARCHAR(12) DEFAULT ''"),('product_id','INTEGER'),
                    ('volume',"VARCHAR(50) DEFAULT ''"),('customer_first',"VARCHAR(100) DEFAULT ''"),
                    ('customer_last',"VARCHAR(100) DEFAULT ''"),('wilaya',"VARCHAR(100) DEFAULT ''"),
                    ('delivery_type',"VARCHAR(50) DEFAULT 'bureau'"),('promo_code',"VARCHAR(30) DEFAULT ''"),
                    ('discount_amount','INTEGER DEFAULT 0')]:
        if col not in ocols: cur.execute(f"ALTER TABLE orders ADD COLUMN {col} {typ}")
    con.commit(); con.close()

WILAYAS = [
    "01 - Adrar","02 - Chlef","03 - Laghouat","04 - Oum El Bouaghi","05 - Batna",
    "06 - Béjaïa","07 - Biskra","08 - Béchar","09 - Blida","10 - Bouira",
    "11 - Tamanrasset","12 - Tébessa","13 - Tlemcen","14 - Tiaret","15 - Tizi Ouzou",
    "16 - Alger","17 - Djelfa","18 - Jijel","19 - Sétif","20 - Saïda",
    "21 - Skikda","22 - Sidi Bel Abbès","23 - Annaba","24 - Guelma","25 - Constantine",
    "26 - Médéa","27 - Mostaganem","28 - M'Sila","29 - Mascara","30 - Ouargla",
    "31 - Oran","32 - El Bayadh","33 - Illizi","34 - Bordj Bou Arréridj","35 - Boumerdès",
    "36 - El Tarf","37 - Tindouf","38 - Tissemsilt","39 - El Oued","40 - Khenchela",
    "41 - Souk Ahras","42 - Tipaza","43 - Mila","44 - Aïn Defla","45 - Naâma",
    "46 - Aïn Témouchent","47 - Ghardaïa","48 - Relizane","49 - El M'Ghair","50 - El Menia",
    "51 - Ouled Djellal","52 - Bordj Badji Mokhtar","53 - Béni Abbès","54 - Timimoun",
    "55 - Touggourt","56 - Djanet","57 - In Salah","58 - In Guezzam",
    "59 - أفالو","60 - باريكا","61 - القنبور","62 - قاضي العاتر","63 - العسيرة",
    "64 - قصر الشلالة","65 - عين واسارة","66 - مسعد","67 - محطة بخاري","68 - بوسة بيبي",
    "69 - الأبيض سيدي الشيخ"
]

# ══════════════════════════════════════
# PUBLIC ROUTES
# ══════════════════════════════════════
@app.route('/')
def index():
    products = Product.query.all()
    return render_template('index.html', products=products)

@app.route('/shop')
def shop_collection():
    products = Product.query.all()
    return render_template('collection.html', products=[p.to_dict() for p in products],
                           title="مجموعتنا النسائية | WOMEN'S COLLECTION")

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get(product_id)
    if not product: return abort(404)
    related = Product.query.filter(
        Product.category == product.category,
        Product.id != product_id
    ).limit(4).all()
    return render_template('product_detail.html', product=product.to_dict(),
                           wilayas=WILAYAS, related=[p.to_dict() for p in related])

@app.route('/api/promo', methods=['POST'])
def check_promo():
    code = request.json.get('code','').strip().upper()
    price = request.json.get('price', 0)
    promo = PromoCode.query.filter_by(code=code, active=True).first()
    if not promo: return jsonify({'valid': False, 'message': 'كود غير صحيح'})
    if promo.uses_left == 0: return jsonify({'valid': False, 'message': 'انتهت صلاحية الكود'})
    if promo.type == 'percent':
        discount = int(price * promo.value / 100)
    else:
        discount = min(promo.value, price)
    return jsonify({'valid': True, 'discount': discount, 'message': f'خصم {promo.value}{"%" if promo.type=="percent" else " DA"} !'})

@app.route('/order', methods=['POST'])
def place_order():
    data = request.form
    first    = data.get('first_name','').strip()
    last     = data.get('last_name','').strip()
    phone    = data.get('phone','').strip()
    wilaya   = data.get('wilaya','').strip()
    delivery = data.get('delivery_type','bureau')
    pname    = data.get('product_name','')
    pid      = data.get('product_id', type=int)
    volume   = data.get('volume','')
    price    = data.get('price', type=int) or 0
    promo_code = data.get('promo_code','').strip().upper()
    discount = data.get('discount_amount', type=int) or 0

    if not all([first, last, phone, wilaya, pname]):
        flash("الرجاء ملء جميع الحقول الإلزامية.", "error")
        return redirect(request.referrer or url_for('index'))

    if promo_code:
        promo = PromoCode.query.filter_by(code=promo_code, active=True).first()
        if promo and promo.uses_left != 0:
            if promo.uses_left > 0: promo.uses_left -= 1
            if promo.uses_left == 0: promo.active = False

    final_price = max(price - discount, 0)
    order = Order(tracking_code=gen_tracking(), product_name=pname, product_id=pid,
                  volume=volume, price=final_price, customer_first=first, customer_last=last,
                  customer_phone=phone, wilaya=wilaya, delivery_type=delivery,
                  promo_code=promo_code, discount_amount=discount)
    db.session.add(order); db.session.commit()

    try:
        wa_msg = (f"🛍️ طلب جديد #{order.tracking_code}\n"
                  f"المنتج: {pname}{' — '+volume if volume else ''}\n"
                  f"السعر: {final_price} DA\n"
                  f"الزبون: {first} {last}\n"
                  f"الهاتف: {phone}\n"
                  f"الولاية: {wilaya}\n"
                  f"التوصيل: {'مكتب' if delivery=='bureau' else 'منزل'}")
        wa_url = f"https://wa.me/{ADMIN_WHATSAPP}?text={wa_msg.replace(chr(10),'%0A')}"
    except: wa_url = None

    return render_template('order_success.html', order=order, wa_url=wa_url)

@app.route('/track', methods=['GET','POST'])
def track_order():
    order = None
    error = None
    if request.method == 'POST':
        code = request.form.get('tracking_code','').strip().upper()
        order = Order.query.filter_by(tracking_code=code).first()
        if not order: error = "لم يتم العثور على الطلب. تحقق من الرقم."
    return render_template('track.html', order=order, error=error)

@app.route('/checkout')
def checkout():
    return render_template('checkout.html')

# ══════════════════════════════════════
# ADMIN ROUTES
# ══════════════════════════════════════
@app.route('/va_admin/login', methods=['GET','POST'])
def admin_login():
    if session.get('admin_logged_in'): return redirect(url_for('admin_dashboard'))
    if request.method == 'POST':
        if request.form.get('username','').strip()==ADMIN_USERNAME and \
           request.form.get('password','').strip()==ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        flash("Identifiants incorrects.", "error")
    return render_template('login.html')

@app.route('/va_admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

@app.route('/va_admin')
@login_required
def admin_dashboard():
    orders   = Order.query.order_by(Order.timestamp.desc()).all()
    products = Product.query.all()
    promos   = PromoCode.query.all()

    today = date.today()
    orders_today  = Order.query.filter(func.date(Order.timestamp)==today).count()
    total_revenue = db.session.query(func.sum(Order.price)).scalar() or 0
    top_products  = db.session.query(Order.product_name, func.count(Order.id).label('cnt'))\
                      .group_by(Order.product_name).order_by(func.count(Order.id).desc()).limit(5).all()
    top_wilayas   = db.session.query(Order.wilaya, func.count(Order.id).label('cnt'))\
                      .group_by(Order.wilaya).order_by(func.count(Order.id).desc()).limit(5).all()

    stats = {'orders_today': orders_today, 'total_orders': len(orders),
             'total_revenue': total_revenue, 'top_products': top_products,
             'top_wilayas': top_wilayas}

    return render_template('admin.html', orders=orders, products=products,
                           promos=promos, stats=stats)

@app.route('/admin/export/orders')
@login_required
def export_orders():
    try:
        import csv, io as sio
        output = sio.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID','Tracking','Product','Volume','Price','Discount','First Name',
                         'Last Name','Phone','Wilaya','Delivery','Promo','Status','Date'])
        for o in Order.query.order_by(Order.timestamp.desc()).all():
            writer.writerow([o.id, o.tracking_code, o.product_name, o.volume, o.price,
                             o.discount_amount, o.customer_first, o.customer_last,
                             o.customer_phone, o.wilaya, o.delivery_type,
                             o.promo_code, o.status, o.timestamp.strftime('%Y-%m-%d %H:%M')])
        output.seek(0)
        return send_file(io.BytesIO(output.getvalue().encode('utf-8-sig')),
                         mimetype='text/csv', as_attachment=True,
                         download_name=f'vanilla_elegance_orders_{date.today()}.csv')
    except Exception as e:
        flash(f"Export error: {e}", "error")
        return redirect(url_for('admin_dashboard'))

@app.route('/order/<int:oid>/delete', methods=['POST'])
@login_required
def delete_order(oid):
    db.session.delete(Order.query.get_or_404(oid)); db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/order/<int:oid>/status', methods=['POST'])
@login_required
def update_order_status(oid):
    o = Order.query.get_or_404(oid)
    o.status = request.form.get('status', o.status); db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/order/<int:oid>/complete', methods=['POST'])
@login_required
def complete_order(oid):
    o = Order.query.get_or_404(oid); o.completed = not o.completed; db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/product/<int:pid>/stock', methods=['POST'])
@login_required
def update_stock(pid):
    p = Product.query.get_or_404(pid)
    ns = request.form.get('stock_quantity', type=int)
    if ns is not None: p.stock_quantity = ns; db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/product/<int:pid>/edit', methods=['POST'])
@login_required
def edit_product(pid):
    p = Product.query.get_or_404(pid)
    p.name = request.form.get('name', p.name).strip()
    orig = request.form.get('original_price','').strip()
    p.original_price = int(orig) if orig.isdigit() else None
    p.category = request.form.get('category', p.category).strip()
    p.description = request.form.get('description', p.description).strip()
    volumes = request.form.getlist('vol_size[]')
    prices  = request.form.getlist('vol_price[]')
    sizes = [{'volume':v.strip(),'price':int(pr)} for v,pr in zip(volumes,prices) if v.strip() and pr.isdigit()]
    p.sizes_json = json.dumps(sizes, ensure_ascii=False)
    if sizes: p.price = sizes[0]['price']
    extra_imgs = p.get_images()
    for f in request.files.getlist('extra_images'):
        if f and f.filename and allowed_file(f.filename):
            ext = f.filename.rsplit('.',1)[1].lower()
            fname = f"product_{uuid.uuid4().hex[:8]}.{ext}"
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
            extra_imgs.append(fname)
    p.images_json = json.dumps(extra_imgs)
    db.session.commit()
    flash(f"Produit mis à jour.", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/product/add', methods=['POST'])
@login_required
def add_product():
    name     = request.form.get('name','').strip()
    category = request.form.get('category','Women').strip()
    desc     = request.form.get('description','').strip()
    stock    = request.form.get('stock_quantity', type=int) or 0
    orig     = request.form.get('original_price','').strip()
    original_price = int(orig) if orig.isdigit() else None
    volumes  = request.form.getlist('vol_size[]')
    prices   = request.form.getlist('vol_price[]')
    sizes = [{'volume':v.strip(),'price':int(pr)} for v,pr in zip(volumes,prices) if v.strip() and pr.isdigit()]
    base_price = sizes[0]['price'] if sizes else (request.form.get('price', type=int) or 0)
    if not name or not base_price:
        flash("Nom et prix requis.", "error"); return redirect(url_for('admin_dashboard'))
    img = 'placeholder.jpg'
    file = request.files.get('image')
    if file and file.filename and allowed_file(file.filename):
        ext = file.filename.rsplit('.',1)[1].lower()
        img = f"product_{uuid.uuid4().hex[:8]}.{ext}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], img))
    extra_imgs = []
    for f in request.files.getlist('extra_images'):
        if f and f.filename and allowed_file(f.filename):
            ext = f.filename.rsplit('.',1)[1].lower()
            fname = f"product_{uuid.uuid4().hex[:8]}.{ext}"
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
            extra_imgs.append(fname)
    db.session.add(Product(name=name, price=base_price, original_price=original_price,
                           image=img, images_json=json.dumps(extra_imgs), stock_quantity=stock,
                           category=category, description=desc,
                           sizes_json=json.dumps(sizes, ensure_ascii=False)))
    db.session.commit()
    flash(f"Produit '{name}' ajouté!", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/product/<int:pid>/delete', methods=['POST'])
@login_required
def delete_product(pid):
    p = Product.query.get_or_404(pid); db.session.delete(p); db.session.commit()
    flash("Produit supprimé.", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/promo/add', methods=['POST'])
@login_required
def add_promo():
    code  = request.form.get('code','').strip().upper()
    type_ = request.form.get('type','percent')
    value = request.form.get('value', type=int) or 0
    uses  = request.form.get('uses_left', type=int) or -1
    if not code or not value:
        flash("Code et valeur requis.", "error"); return redirect(url_for('admin_dashboard'))
    if PromoCode.query.filter_by(code=code).first():
        flash("Ce code existe déjà.", "error"); return redirect(url_for('admin_dashboard'))
    db.session.add(PromoCode(code=code, type=type_, value=value, uses_left=uses))
    db.session.commit(); flash(f"Code '{code}' créé!", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/promo/<int:pid>/delete', methods=['POST'])
@login_required
def delete_promo(pid):
    db.session.delete(PromoCode.query.get_or_404(pid)); db.session.commit()
    flash("Code supprimé.", "success"); return redirect(url_for('admin_dashboard'))

@app.route('/admin/promo/<int:pid>/toggle', methods=['POST'])
@login_required
def toggle_promo(pid):
    p = PromoCode.query.get_or_404(pid); p.active = not p.active; db.session.commit()
    return redirect(url_for('admin_dashboard'))

with app.app_context():
    db.create_all(); migrate_db()

if __name__ == '__main__':
    app.run(debug=True)
