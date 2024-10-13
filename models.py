from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import  ForeignKey
from sqlalchemy.orm import relationship

db = SQLAlchemy()

# Tabla intermedia para los favoritos
user_favorites = db.Table('user_favorites',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('store_id', db.Integer, db.ForeignKey('store.id'), primary_key=True)
)

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    birth_date = db.Column(db.Date, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)  # Nuevo: para verificar si es admin
    suspended_until = db.Column(db.DateTime, nullable=True)  # Nuevo: fecha hasta que el usuario está suspendido
    
    stores = db.relationship('Store', backref='owner', lazy=True)
    products = db.relationship('Product', backref='creator', lazy=True)
    comments = db.relationship('Comment', backref='comment_user', lazy=True)
    favorite_stores = db.relationship('Store', secondary=user_favorites,
                                       lazy='subquery',
                                       backref=db.backref('favorited_by', lazy=True))


class Store(db.Model):
    __tablename__ = 'store'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    address = db.Column(db.String(255), nullable=True)
    rating = db.Column(db.Float, nullable=False, default=0)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    suspended_until = db.Column(db.DateTime, nullable=True)  # Nuevo: para suspender la tienda
    
    store_products = db.relationship('Product', backref='store_relation', lazy=True)
    comments = db.relationship('Comment', backref='store', lazy=True)
    news = db.relationship('News', backref='store', lazy=True)

class Product(db.Model):
    __tablename__ = 'product'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    store_id = db.Column(db.Integer, ForeignKey('store.id'), nullable=False)
    user_id = db.Column(db.Integer, ForeignKey('user.id'), nullable=False)  # Clave foránea para User

    # Usamos solo backref aquí
    store = relationship('Store', backref='products')
    created_products = relationship('User', backref='created_products')  # Cambiado a 'created_products'

class News(db.Model):
    __tablename__ = 'news'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    content = db.Column(db.Text, nullable=False)
    published_date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    store_id = db.Column(db.Integer, db.ForeignKey('store.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)  # Nuevo: para inhabilitar la noticia

    news_article = db.relationship('Comment', backref='news_article', lazy=True)

    def __repr__(self):
        return f'<News {self.title}>'

class Comment(db.Model):
    __tablename__ = 'comment'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    news_id = db.Column(db.Integer, db.ForeignKey('news.id'), nullable=True)
    store_id = db.Column(db.Integer, db.ForeignKey('store.id'), nullable=True)
    published_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)  # Nuevo: para inhabilitar el comentario

    user = db.relationship('User', backref='user_comments', lazy=True)
    news = db.relationship('News', backref='comments', lazy=True)
    store_comments = db.relationship('Store', backref='store_comments', lazy=True)

