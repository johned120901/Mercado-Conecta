from flask import Flask, render_template, request, redirect, session, flash
from models import db, User, Store, Product, Comment, News, user_favorites
from config import Config
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta


app = Flask(__name__)
app.config.from_object(Config)

# Inicializamos la base de datos
db.init_app(app)

@app.context_processor
def inject_user():
    user = None
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
    return dict(user=user)


@app.route('/')
def index():
    recent_news = News.query.order_by(News.published_date.desc()).limit(5).all()
    comments = {news.id: news.comments for news in recent_news}
    
    user = None
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
    
    return render_template('index.html', recent_news=recent_news, comments=comments, user=user)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        if user and check_user_suspended(user):
            flash(f'Tu cuenta está suspendida hasta {user.suspended_until.strftime("%Y-%m-%d %H:%M")}.', 'error')
            return redirect('/login')

        if user and user.password == password:
            session['user_id'] = user.id
            session['user_is_admin'] = user.is_admin
            return redirect('/')
        else:
            flash('Nombre de usuario o contraseña incorrectos.', 'error')

    return render_template('login.html')


# Ruta para el registro de usuarios
from sqlalchemy.exc import IntegrityError

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        phone = request.form['phone']
        birth_date_str = request.form['birth_date']
        
        # Convertir la cadena de fecha a un objeto date
        try:
            birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Fecha de nacimiento no válida. Usa el formato YYYY-MM-DD.', 'error')
            return redirect('/register')

        # Verificar si el nombre de usuario o email ya existe
        existing_user = User.query.filter_by(username=username).first()
        existing_email = User.query.filter_by(email=email).first()
        if existing_user:
            flash('El nombre de usuario ya existe. Elige otro.', 'error')
            return redirect('/register')
        if existing_email:
            flash('El correo electrónico ya está en uso. Usa otro.', 'error')
            return redirect('/register')

        new_user = User(
            username=username, 
            password=password, 
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            birth_date=birth_date
        )

        try:
            db.session.add(new_user)
            db.session.commit()
            return redirect('/login')
        except IntegrityError as e:
            db.session.rollback()
            flash(f'Error al registrar el usuario: {str(e)}', 'error')
            return redirect('/register')
        except Exception as e:
            db.session.rollback()
            flash(f'Ocurrió un error inesperado: {str(e)}', 'error')
            return redirect('/register')

    return render_template('register.html')




# Ruta para cerrar sesión
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect('/login')

# Ruta para editar el perfil
@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        return redirect('/login')
    
    user = User.query.get(session['user_id'])
    
    if request.method == 'POST':
        user.username = request.form['username']
        user.first_name = request.form['first_name']
        user.last_name = request.form['last_name']
        birth_date_str = request.form['birth_date']  # La fecha llega como cadena
        user.birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date() 
        user.email = request.form['email']
        user.phone = request.form['phone']
        
        db.session.commit()
        flash('Perfil actualizado con éxito.', 'success')
        return redirect('/profile')
    
    return render_template('edit_profile.html', user=user)



# Ruta para ver todas las tiendas
@app.route('/stores')
def stores():
    if 'user_id' not in session:
        return redirect('/login')
    # Obtener todas las tiendas, excepto las del usuario actual
    other_stores = Store.query.filter(Store.owner_id != session['user_id']).all()
    return render_template('stores.html', stores=other_stores)

# Ruta para el perfil del usuario
@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect('/login')
    user = User.query.get(session['user_id'])
    return render_template('profile.html', user=user)

@app.route('/profile/<int:user_id>')
def user_profile(user_id):
    if 'user_id' not in session:
        return redirect('/login')

    user = User.query.get_or_404(user_id)  # Obtener el usuario por ID
    return render_template('profile.html', user=user)


@app.route('/comment/<int:news_id>', methods=['POST'])
def add_comment(news_id):
    if 'user_id' not in session:
        return redirect('/login')  # Redirige a la página de inicio de sesión si no está autenticado

    content = request.form['comment']
    new_comment = Comment(content=content, user_id=session['user_id'], news_id=news_id)

    # Verificar si el comentario está relacionado con una tienda
    news = News.query.get(news_id)  # Obtener la noticia para la que se está comentando
    if news:
        new_comment.store_id = news.store_id  # Relacionar el comentario con la tienda correspondiente

    db.session.add(new_comment)
    db.session.commit()

    # Redirigir al usuario a la misma página de la noticia o la tienda
    return redirect(request.referrer or '/') 

@app.route('/create_store', methods=['GET', 'POST'])
def create_store():
    if 'user_id' not in session:
        return redirect('/login')
    
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        address = request.form['address']
        new_store = Store(name=name, description=description, address=address, rating=0, owner_id=session['user_id'])
        
        db.session.add(new_store)
        db.session.commit()
        
        # Crear noticia sobre la creación de la tienda
        # Crear noticia sobre la creación de la tienda
        news_title = f'Tienda "{new_store.name}" creada'
        news_content = f'''
            <strong>La tienda "{new_store.name}" ha sido creada con éxito.</strong><br>
            <strong>Descripción:</strong> {new_store.description}<br>
            <strong>Dirección:</strong> {new_store.address}
            '''
        news = News(title=news_title, content=news_content, user_id=session['user_id'], store_id=new_store.id)
        db.session.add(news)
        db.session.commit()

        return redirect(f'/store/{new_store.id}')  # Redirigir a la página de vista de la tienda creada

    return render_template('create_store.html')

@app.route('/edit_store/<int:store_id>', methods=['GET', 'POST'])
def edit_store(store_id):
    if 'user_id' not in session:
        return redirect('/login')

    store = Store.query.get_or_404(store_id)
    
    if request.method == 'POST':
        updated_fields = []
        
        # Comprobar y actualizar solo los campos que fueron cambiados
        if request.form['name'] != store.name:
            store.name = request.form['name']
            updated_fields.append(f'<strong>Nombre:</strong> {store.name}')
        
        if request.form['description'] != store.description:
            store.description = request.form['description']
            updated_fields.append(f'<strong>Descripción:</strong> {store.description}')
        
        if request.form['address'] != store.address:
            store.address = request.form['address']
            updated_fields.append(f'<strong>Dirección:</strong> {store.address}')

        # Crear noticia solo si hay campos actualizados
        if updated_fields:
            news_title = f'Tienda "{store.name}" editada'
            news_content = f'La tienda ha sido editada con éxito:<br>' + '<br>'.join(updated_fields)
            news = News(title=news_title, content=news_content, user_id=session['user_id'], store_id=store.id)
            db.session.add(news)

        db.session.commit()

        return redirect(f'/store/{store.id}')

    return render_template('edit_store.html', store=store)


@app.route('/add_product/<int:store_id>', methods=['GET', 'POST'])
def add_product(store_id):
    if 'user_id' not in session:
        return redirect('/login')

    store = Store.query.get_or_404(store_id)

    if request.method == 'POST':
        product_names = request.form.getlist('name[]')
        product_prices = request.form.getlist('price[]')

        try:
            product_list = []  # Lista para almacenar los nombres de los productos añadidos

            for name, price in zip(product_names, product_prices):
                temporal_price = price.replace('$', '').split()
                product_price = int(temporal_price[0].replace('.', '').strip())
                new_product = Product(name=name, price=product_price, store_id=store_id, user_id=session['user_id'])  # Crear el producto
                db.session.add(new_product)
                product_list.append(f"<li>{new_product.name}</li>")  # Agregar el nombre del producto a la lista

            db.session.commit()  # Confirmar los cambios a la base de datos
            
            # Crear noticia sobre todos los productos añadidos
            product_list_html = ''.join(product_list)  # Convertir lista a HTML
            news_title = f'Se han agregado los siguientes productos a la tienda "{store.name}":'
            news_content = f'{news_title}<ul>{product_list_html}</ul>'
            news = News(title=news_title, content=news_content, user_id=session['user_id'], store_id=store_id)
            db.session.add(news)
            db.session.commit()  # Confirmar la noticia

            return redirect(f'/store/{store_id}')

        except Exception as e:
            db.session.rollback()  # Deshacer cambios si hay un error
            flash('Error al agregar productos: ' + str(e), 'error')

    return render_template('add_product.html', selected_store_id=store_id)


@app.route('/store/<int:store_id>')
def view_store(store_id):
    if 'user_id' not in session:
        return redirect('/login')

    store = Store.query.get_or_404(store_id)
    
    # Verifica si la tienda está suspendida
    if check_store_suspended(store):
        flash('Esta tienda está temporalmente inaccesible.', 'error')
        redirect(request.referrer or '/')   # Redirigir a la página de inicio

    comments = store.comments  # Obtener comentarios de la tienda
    products = store.products   # Obtener productos de la tienda

    # Obtener las noticias relacionadas con la tienda y ordenarlas de más reciente a más antigua
    news = News.query.filter_by(store_id=store.id).order_by(News.published_date.desc()).all()

    is_owner = store.owner_id == session['user_id']

    # Comprobar si la tienda está en los favoritos del usuario
    user = User.query.get(session['user_id'])
    is_favorite = store in user.favorite_stores  # Comprobar si la tienda está en los favoritos

    return render_template('view_store.html', store=store, comments=comments, products=products, is_owner=is_owner, news=news, is_favorite=is_favorite, user=user)




@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    if 'user_id' not in session:
        return redirect('/login')

    product = Product.query.get_or_404(product_id)

    if request.method == 'POST':
        old_name = product.name  # Guardar el nombre anterior del producto
        product.name = request.form['product_name']
        temporal_price = request.form['product_price'].replace('$', '').split()
        product_price = int(temporal_price[0].replace('.', '').strip())
        product.price = product_price
        db.session.commit()

        # Crear noticia sobre la modificación del producto
        news_title = f'Producto modificado: "{old_name}" ha sido cambiado a "{product.name}"'
        news_content = f'El producto ha sido modificado. Nuevo nombre: <strong>{product.name}</strong>.<br/>Precio: <strong>${product.price}</strong>.'
        news = News(title=news_title, content=news_content, user_id=session['user_id'], store_id=product.store_id)
        db.session.add(news)
        db.session.commit()

        return redirect(f'/store/{product.store_id}')

    return render_template('edit_product.html', product=product)


@app.route('/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    if 'user_id' not in session:
        return redirect('/login')

    # Cargar el producto y su tienda en una misma sesión
    product = Product.query.options(db.joinedload(Product.store)).get_or_404(product_id)
    store_id = product.store_id  # Guardar el ID de la tienda antes de eliminar el producto

    # Eliminar el producto
    db.session.delete(product)
    db.session.commit()

    # Crear noticia sobre la eliminación del producto
    news_title = f'Producto eliminado: "{product.name}"'
    news_content = f'El producto "<strong>{product.name}</strong>" ha sido eliminado de la tienda "<strong>{product.store.name}</strong>".'
    news = News(title=news_title, content=news_content, user_id=session['user_id'], store_id=store_id)
    db.session.add(news)
    db.session.commit()

    return redirect(f'/store/{store_id}')


@app.route('/add_favorite/<int:store_id>', methods=['POST'])
def add_favorite(store_id):
    if 'user_id' not in session:
        return redirect('/login')

    store = Store.query.get_or_404(store_id)
    user = User.query.get(session['user_id'])
    
    # Agregar la tienda a los favoritos
    if store not in user.favorite_stores:
        user.favorite_stores.append(store)
        db.session.commit()

    return redirect(f'/store/{store_id}')

@app.route('/remove_favorite/<int:store_id>', methods=['POST'])
def remove_favorite(store_id):
    if 'user_id' not in session:
        return redirect('/login')

    store = Store.query.get_or_404(store_id)
    user = User.query.get(session['user_id'])

    # Eliminar la tienda de los favoritos
    if store in user.favorite_stores:
        user.favorite_stores.remove(store)
        db.session.commit()

    return redirect(f'/store/{store_id}')


@app.route('/favorites')
def favorites():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    # Obtener las tiendas favoritas del usuario usando una consulta más explícita
    favorite_stores = (
        Store.query
        .join(user_favorites)
        .filter(user_favorites.c.user_id == user_id)
        .all()
    )

    return render_template('favorites.html', favorite_stores=favorite_stores)


@app.route('/rate_store/<int:store_id>', methods=['POST'])
def rate_store(store_id):
    if 'user_id' not in session:
        return redirect('/login')

    store = Store.query.get_or_404(store_id)
    rating = float(request.form['rating'])  # Obtener el valor del rango

    # Actualizar la puntuación de la tienda
    store.rating = rating
    db.session.commit()

    flash('Calificación actualizada con éxito.', 'success')  # Mensaje de éxito
    return redirect(f'/store/{store.id}')  # Redirigir a la tienda
# Verificar si el usuario está suspendido
def check_user_suspended(user):
    if user.suspended_until and user.suspended_until > datetime.utcnow():
        return True
    return False

# Verificar si la tienda está suspendida
def check_store_suspended(store):
    if store.suspended_until and store.suspended_until > datetime.utcnow():
        return True
    return False

@app.route('/admin')
def admin_lobby():
    if 'user_id' not in session:
        return redirect('/login')

    admin_user = User.query.get(session['user_id'])
    if not admin_user.is_admin:
        flash('No tienes permisos para acceder a esta sección.', 'error')
        return redirect('/')

    return render_template('admin_lobby.html')


# Ruta para la administración de usuarios
@app.route('/admin/users', methods=['GET'])
def admin_users():
    if 'user_id' not in session:
        return redirect('/login')

    admin_user = User.query.get(session['user_id'])
    if not admin_user.is_admin:
        flash('No tienes permisos para realizar esta acción.', 'error')
        return redirect('/')

    # Obtener todos los usuarios que no son administradores
    users = User.query.filter_by(is_admin=False).all()  # Filtrar usuarios no administradores
    return render_template('admin_users.html', users=users)


# Ruta para ver la lista de tiendas (para admin)
@app.route('/admin/stores', methods=['GET'])
def admin_stores():
    if 'user_id' not in session:
        return redirect('/login')

    admin_user = User.query.get(session['user_id'])
    if not admin_user.is_admin:
        flash('No tienes permisos para acceder a esta sección.', 'error')
        return redirect('/')

    stores = Store.query.all()
    return render_template('admin_stores.html', stores=stores)

# Ruta para suspender a un usuario
@app.route('/admin/suspend_user/<int:user_id>', methods=['POST'])
def suspend_user(user_id):
    if 'user_id' not in session:
        return redirect('/login')
    
    admin_user = User.query.get(session['user_id'])
    if not admin_user.is_admin:
        flash('No tienes permisos para realizar esta acción.', 'error')
        return redirect('/')

    suspension_days = int(request.form.get('days', 0))
    user = User.query.get_or_404(user_id)
    user.suspended_until = datetime.utcnow() + timedelta(days=suspension_days)
    db.session.commit()
    
    return redirect('/admin/users')

# Ruta para suspender una tienda (ya lo tienes definido)
@app.route('/admin/suspend_store/<int:store_id>', methods=['POST'])
def suspend_store(store_id):
    if 'user_id' not in session:
        return redirect('/login')

    admin_user = User.query.get(session['user_id'])
    if not admin_user.is_admin:
        flash('No tienes permisos para realizar esta acción.', 'error')
        return redirect('/')

    suspension_days = int(request.form.get('days', 0))
    store = Store.query.get_or_404(store_id)
    store.suspended_until = datetime.utcnow() + timedelta(days=suspension_days)
    db.session.commit()

    return redirect('/admin/stores')


# Ruta para inhabilitar un comentario
@app.route('/admin/disable_comment/<int:comment_id>', methods=['POST'])
def disable_comment(comment_id):
    if 'user_id' not in session:
        return redirect('/login')

    admin_user = User.query.get(session['user_id'])
    if not admin_user.is_admin:
        flash('No tienes permisos para realizar esta acción.', 'error')
        return redirect(request.referrer or '/') 

    comment = Comment.query.get_or_404(comment_id)
    comment.is_active = False  # Marcar comentario como suspendido
    db.session.commit()

    return redirect(request.referrer or '/') 

# Rutas para ver si un usuario o tienda está suspendida
@app.before_request
def before_request():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if check_user_suspended(user):
            flash('Tu cuenta ha sido suspendida temporalmente.', 'error')
            return redirect('/login')
        
        # Ruta para inhabilitar una noticia
@app.route('/admin/disable_news/<int:news_id>', methods=['POST'])
def disable_news(news_id):
    if 'user_id' not in session:
        return redirect('/login')

    admin_user = User.query.get(session['user_id'])
    if not admin_user.is_admin:
        flash('No tienes permisos para realizar esta acción.', 'error')
        return redirect(request.referrer or '/') 

    news = News.query.get_or_404(news_id)
    news.is_active = False  # Aquí se inhabilita la noticia
    db.session.commit()

    return redirect(request.referrer or '/') 

# Ruta para quitar el baneo de un usuario
@app.route('/admin/unsuspend_user/<int:user_id>', methods=['POST'])
def unsuspend_user(user_id):
    if 'user_id' not in session:
        return redirect('/login')

    admin_user = User.query.get(session['user_id'])
    if not admin_user.is_admin:
        flash('No tienes permisos para realizar esta acción.', 'error')
        return redirect('/')

    user = User.query.get_or_404(user_id)
    user.suspended_until = None  # Quitar la fecha de suspensión
    db.session.commit()

    return redirect('/admin/users')

# Ruta para desbanear una tienda
@app.route('/admin/unsuspend_store/<int:store_id>', methods=['POST'])
def unsuspend_store(store_id):
    if 'user_id' not in session:
        return redirect('/login')

    admin_user = User.query.get(session['user_id'])
    if not admin_user.is_admin:
        flash('No tienes permisos para realizar esta acción.', 'error')
        return redirect('/')

    store = Store.query.get_or_404(store_id)
    store.suspended_until = None  # Eliminar la suspensión
    db.session.commit()
    return redirect('/admin/stores')

# Iniciar la aplicación y crear las tablas de la base de datos si no existen
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Crea todas las tablas en la base de datos si no existen
    app.run(debug=True)
