from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.views.generic.edit import UpdateView, CreateView, DeleteView
from django.views.generic import ListView, DetailView
from django.contrib.auth import login
from .forms import ProfileForm, UserForm, ProductItemForm
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
import requests
import random
from .models import *
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from . serializers import bookSerializer, categoriesSerializer
from django.db.models import Q
from django.http import JsonResponse
from django.contrib.staticfiles.templatetags.staticfiles import static

class bookList(APIView):
    def get(self, request):
        query = self.request.GET.get('q')
        books_per_page = 16
        page_num = 0
        if self.request.GET.get('cat') != None:
            books = Book.objects.filter(Q(categories__icontains=query))
        else:
            books = Book.objects.filter(Q(title__icontains=query) | Q(author__icontains=query) | Q(publisher__icontains=query) | Q(categories__icontains=query))

        total_books = len(books)

        if total_books/books_per_page != 0:
            total_pages = (total_books // books_per_page) + 1
        else:
            total_pages = (total_books // books_per_page)

        if self.request.GET.get('page') != None:
            page_num = int(self.request.GET.get('page'))
            books = books[page_num*books_per_page:page_num*books_per_page+books_per_page]
        else:
            page_num = 0
            books = books[0:books_per_page]
        return render(request, 'search_results.html', {
            'title': f'Results for {query}',
            'query': query,
            'books': books,
            'page_num': page_num,
            'total_pages': range(total_pages),
            'last_page': total_pages-1,
            'sidebar': True
        })

class categoriesList(APIView):
    def get(self, request):
        categories = Book.objects.values('categories').order_by('categories').distinct('categories')
        serializer = categoriesSerializer(categories, many=True)
        return Response(serializer.data)

def categories_api(request):
    if request.method == 'GET':
        categories_list = []
        categories = Book.objects.values('categories').order_by('categories').distinct('categories')
        for cat in categories:
            categories_list.append(cat['categories'])
        return JsonResponse({'categores':categories_list}, safe=False)

def signup(request):
    error_message = ''
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('index')
        else:
            error_message = 'Invalid credentials - try again'
    form = UserCreationForm()
    context = {'form': form, 'error_message': error_message}
    return render(request, 'registration/signup.html', context)

class ProfileUpdate(LoginRequiredMixin, UpdateView):
    model = Profile
    fields = ['phone', 'address', 'postal_code', 'city', 'country', 'birthday']

def home(request):
    books = Book.objects.all()
    return render(request, 'home.html', {
        'title': 'Home Page',
        'books': books,
        'sidebar': True
    })

def about(request):
    return render(request, 'about.html', {
        'title': 'About Page'
    })

def books_index(request):
    books = Book.objects.all()
    form = ProductItemForm()
    books_per_page = 80

    total_books = len(books)

    if total_books/books_per_page != 0:
        total_pages = (total_books // books_per_page) + 1
    else:
        total_pages = (total_books // books_per_page)

    if request.GET.get('page') != None:
        page_num = int(request.GET.get('page'))
        books = books[page_num*books_per_page:page_num*books_per_page+books_per_page]
    else:
        page_num = 0
        books = books[0:books_per_page]
    return render(request, 'books/index.html', {
        'title': 'Books',
        'query': '',
        'books': books,
        'page_num': page_num,
        'total_pages': range(total_pages),
        'last_page': total_pages-1,
        'sidebar': True
    })
    return render(request, 'books/index.html', { 'books': books, 'product_item_form': form })

def books_detail(request, book_id):
    book = Book.objects.get(id=book_id)
    form = ProductItemForm()
    return render(request, 'books/detail.html', {'book': book, 'sidebar': True, 'product_item_form': form })

def orders_index(request):
    orders = Order.objects.all()
    return render(request, 'orders/index.html', {'orders': orders})

def orders_detail(request, order_id):
    order = Order.objects.get(pk=order_id)
    user_items =  ProductItem.objects.filter(user_id=request.user.id)
    product_items = user_items.filter(order_id=order_id)
    print(order)
    print(user_items)
    print(product_items)
    return render(request, 'orders/detail.html', {'order': order, 'product_items':product_items})

@login_required
def profiles_index(request):
    profiles = Profile.objects.all()
    return render(request, 'profiles/index.html', { 'profiles': profiles })

@login_required
def cart_index(request):
    books = Book.objects.all()
    product_items = ProductItem.objects.all()
    orders = Order.objects.all()
    return render(request, 'cart/index.html', {'product_items': product_items, 'books': books, 'orders': orders})


@login_required
def seed(request):
    if request.user.is_superuser:
        return render(request, 'seed.html', {
            'title': 'Seed DB'
        })
    else:
        return redirect('index')

@login_required
def seed_db(request):
    if request.user.is_superuser:
        if request.method == 'GET':
            resp = requests.get(request.GET['link'])

            if resp.status_code != 200:
                print('Something went wrong')
                return JsonResponse({'status': 'nok'})
            else:
                items = resp.json()['items']

                for item in items:
                    if item['volumeInfo'].get('authors') and len(item['volumeInfo'].get('authors')) > 1 :
                        authors = ", ".join(map(str, item['volumeInfo'].get('authors', ['N/A'])))
                    else:
                        authors = item['volumeInfo'].get('authors', ['N/A'])[0]
                    if item['volumeInfo'].get('categories') and len(item['volumeInfo'].get('categories')) > 1:
                        categories = ", ".join(map(str, item['volumeInfo'].get('categories', ['Others'])))
                    else:
                        categories = item['volumeInfo'].get('categories', ['Others'])[0]
                    pages = item['volumeInfo'].get('pageCount', 10)
                    if item['saleInfo']:
                        if (item['saleInfo']['saleability'] == 'FOR_SALE'):
                            price = float(item['saleInfo']['listPrice']['amount'])
                        else:
                            price = round(random.uniform(1.99, 99.99),2)
                    else:
                        price = round(random.uniform(1.99, 99.99),2)
                    industry_identifiers = item['volumeInfo'].get('industryIdentifiers', [])
                    if len(industry_identifiers):
                        isbn = industry_identifiers[0].get('identifier', '123456789123')
                    else:
                        isbn = '123456789123'
                    if item['volumeInfo'].get('imageLinks'):
                        thumbnail = item['volumeInfo']['imageLinks']['thumbnail']
                    else:
                        thumbnail = static('image/no-image.jpg')
                    Book.objects.create(
                        isbn=isbn,
                        title=item['volumeInfo']['title'],
                        year_published=item['volumeInfo'].get('publishedDate', '2011'),
                        author=authors,
                        publisher=item['volumeInfo'].get('publisher', 'N/A'),
                        description=item['volumeInfo'].get('description', 'N/A'),
                        categories=categories,
                        pages=pages,
                        price=price,
                        quantity=random.randint(1, 30),
                        book_img=thumbnail
                    )
                return JsonResponse({'status': 'ok'})
    else:
        return redirect('index')

def add_product_item_index(request, book_id):
    book = Book.objects.get(pk=book_id)
    user_items = ProductItem.objects.filter(user=request.user)
    order_items = user_items.filter(order__isnull=True)
    items = order_items.filter(book_id=book.id)
    for item in items:
        item.quantity += 1
        item.save()
        return redirect('/cart/')
    new_product_item = ProductItem(quantity=0)
    new_product_item.book_id = book_id
    new_product_item.price = book.price
    new_product_item.quantity += 1
    new_product_item.user_id = request.user.id
    new_product_item.save()
    return redirect('/cart/')

def add_product_item(request, book_id):
    form = ProductItemForm(request.POST)
    book = Book.objects.get(pk=book_id)
    user_items = ProductItem.objects.filter(user=request.user)
    order_items = user_items.filter(order__isnull=True)
    items = order_items.filter(book_id=book.id)
    for item in items:
        item.quantity = request.POST('increase')
        item.save()
        return redirect('/cart/')
    if form.is_valid():
        new_product_item = form.save(commit=False)
        new_product_item.book_id = book_id
        book = Book.objects.get(pk=book_id)
        new_product_item.price = book.price
        new_product_item.user_id = request.user.id
        new_product_item.save()
    return redirect('/cart/')

def delete_product_item(request, product_item_id):
    prod = ProductItem.objects.get(pk=product_item_id)
    prod.delete()
    return redirect('/cart/')

def add_order(request):
    user_items = ProductItem.objects.filter(user=request.user)
    items = user_items.filter(order__isnull=True)
    order = Order(user_id=request.user.id)
    order.save()
    for item in items:
        item.order_id = order.id
        item.save()
    return redirect('/cart/')

def increase_quantity(request, product_item_id):
    product = ProductItem.objects.get(pk=product_item_id)
    product.quantity = request.POST.get('increase')
    product.save()
    return redirect('/cart/')

