from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
import json
from .models import Book, StaredBook
from users_b.models import User
from django.core import serializers
from sale.models import SaleImage
from search.search_book import cacheBook

def home(request):
    return HttpResponse("Welcome", content_type="application/json")
    
    
@csrf_exempt
def insert_book(request):
    if request.method == 'POST':
        full_title = request.POST.get('full_title', "")
        link = request.POST.get('link', "")
        uniform_title = request.POST.get('uniform_title', "")
        if len(full_title) > 0 and len(link) > 0 and len(uniform_title) > 0:
            try:
                #insert the book into the database
                Book.objects.create(full_title=full_title, link=link, uniform_title=uniform_title)
                return HttpResponse(json.dumps({'response': 'inserted'}), content_type="application/json")
            except:
                print("shit")
                return HttpResponse(json.dumps({'response': 'looks like there was a problem entering it'}), 
                                    content_type="application/json")
        else:
            return HttpResponse(json.dumps({'response': 'looks like there is no data'}),
                                content_type="application/json")
                                
    else:
        return HttpResponse(json.dumps({'response': 'send correct request'}),
                            content_type="application/json")
                            
                            
@csrf_exempt
def new_search(request):
    if request.method == 'POST':
        search_string = request.POST.get('search_string', "")
        return HttpResponse(json.dumps({'response': search_string}),
                            content_type="application/json")
    else:
        return HttpResponse(json.dumps({'response': 'please send the correct request'}),
                            content_type="application/json")
                            
@csrf_exempt
def search_book(request):
    if request.method == 'GET':
        search_query = request.GET.get('search_string')
        #searching for books
        books = Book.objects.filter(full_title__icontains=search_query, link="")
        return HttpResponse(
            serializers.serialize("json", books),
            content_type="application/json")
                
@csrf_exempt
def star_book(request, p_id="1"):
    if request.method == 'POST':
        #make request
        user_id = request.POST.get('user_id')
        user = User.objects.get(user_id=user_id)
        book = Book.objects.get(pk=p_id)
        #creating the book
        StaredBook.objects.create(book=book, user=user)
        return HttpResponse(json.dumps({'response': 'done'}), 
                            content_type="application/json")
    else:
        return HttpResponse(json.dumps({'response': 'welcome'}),
                            content_type="application/json")
                            
@csrf_exempt
def get_book_images(reqeust):
   pass
   
@csrf_exempt
def bookDetails(request):
    if request.method == 'POST':
        bookId = request.POST.get('book_id')
        if bookId is not None:
            book = Book.objects.get(pk=bookId)
            return HttpResponse(serializers.serialize("json", [book])[1:-1],
                                content_type="application/json")
        else:
            return HttpResponse(json.dumps({'error': 'id parameter was missing.'}),
                                content_type="application/json")
    else:
        return HttpResponse(json.dumps({'error': 'Only POST requsest is allowed.'}),
                            content_type="application/json")


@csrf_exempt
def cacheBookDetails(request):
    if request.method == 'POST':
        data = request.POST.get('book_details')
        #cache the book here
        return HttpResponse(json.dumps({'response': 'book cached'},
                            content_type="application/json"))
    else:
        return HttpResponse(json.dumps({'response': 'only POST requests'},
                            content_type="application/json"))

