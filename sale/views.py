import json
import pdb
import time
import requests
import redis
import bmemcached
from hashlib import sha256
from datetime import datetime

from django.http import QueryDict
from django.shortcuts import render
from django.http import HttpResponse
from django.core import serializers
from django.views.generic import View
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ObjectDoesNotExist
from django.core.serializers.json import DjangoJSONEncoder

from search.models import Book
from users_b.models import User
from scansell.utils import ServeResponse

import sale.exceptions
from sale.bid import Bid
from sale.location import Location
from sale.notifications import Notification
from sale.utils import MinPQ, MemcacheWrapper
from sale.exceptions import UserForIDNotFoundException
from sale.feed import generate_feed, get_relative_feed, GeoFeed
# from sale.notifications2 import Notification, BOOK_EMOJI, SALE_EMOJI
from sale.models import Sale, SaleInterest, SaleImage, SaleNotification


# creating a new redis server
r = redis.Redis(host='pub-redis-18592.us-east-1-2.4.ec2.garantiadata.com',
                port=18592,
                password='kiran@cr7')
mc = bmemcached.Client('pub-memcache-17929.us-east-1-2.1.ec2.garantiadata.com:17929',
                        'kiran',
                        'kiran@cr7')
memcache = MemcacheWrapper(mc)

# Create your views here.
def home(request):
    sale = Sale.objects.all()[0]
    sale2 = Sale.objects.all()[1]
    refLocation = Location(32.5903056,-85.5284747)
    print(sale.compareTo(sale2, refLocation))
    return HttpResponse("Welcome to the Sale Model App")


#simple title case string view for better type face on app
@csrf_exempt
def title_case_string(request):
    if request.method == 'POST':
        string = request.POST.get('string', "")
        return HttpResponse(json.dumps({'string': string.title()}),
                            content_type="application/json")
    else:
        return HttpResponse(json.dumps({'response': 'please send the correct request'}),
                            content_type="application/json")

@csrf_exempt
def new_sale_insert(request):
    if request.method == 'POST':
        return HttpResponse(json.dumps({'response': 0}),
                            content_type="application/json")
    else:
        return HttpResponse(json.dumps({'response': 'Please send the correct request'}),
                            content_type="application/json")

def redis_test(request):
    return HttpResponse("redis cache")

@csrf_exempt
def create_locale(request):
    ''' This view creates the address for the sale.
        Address format:
        Route, Admininstrative Area Level 3 , Locality, Admininstrative Area Level 2, Admininstrative Level 1,
        State'''
    if request.method == 'POST':
        locale = []
        latitude = request.POST.get('latitude', "")
        longitude = request.POST.get('longitude', "")
        #sending request to google to create locale
        url = "http://maps.googleapis.com/maps/api/geocode/json?latlng=" + latitude + "," + longitude
        try:
            response = json.loads(requests.get(url).content)
        except:
            return_response = "nil"
        #getting the info that we need.
        for obj in response["results"][0]["address_components"]:
            if "route" in obj["types"]:
                locale.append(obj["long_name"])
            if "administrative_area_level_3" in obj["types"]:
                locale.append(obj["long_name"])
            if "locality" in obj["types"]:
                locale.append(obj["long_name"])
            if "administrative_area_level_2" in obj["types"]:
                locale.append(obj["long_name"])
            if "administrative_area_level_1" in obj["types"]:
                locale.append(obj["short_name"])
        return_response = ','.join(locale).upper()
        return HttpResponse(json.dumps({'response': return_response}),
                            content_type="application/json")
    else:
        return HttpResponse(json.dumps({'response': 'please send the correct request'}),
                            content_type="application/json")


@csrf_exempt
def sale_notification(request):
    if request.method == 'POST':
        #get the notif data
        data = {'notif_type': request.POST.get('notif_type', ""),
                'seller_id': request.POST.get('seller_id', ""),
                'seller_username': request.POST.get('seller_username', ""),
                'sale_id': request.POST.get('sale_id', ""),
                'buyer_id': request.POST.get('buyer_id', ""),
                'buyer_username': request.POST.get('buyer_username', "")}
        if data['notif_type'] == "1":
            notif = Notification(1, data)
            return HttpResponse(json.dumps(notif.set_notif_type_1()), content_type="application/json")
        if data['notif_type'] == "2":
            notif = Notification(2, data)
            return HttpResponse(json.dumps(notif.set_notif_type_2(request.POST.get('notif_1_id', ""))), content_type="application/json")
    else:
        return HttpResponse(json.dumps({'response': 'please send the correct request'}),
                            content_type="application/json")

@csrf_exempt
def get_notifications(request):
    user_id = request.GET.get('user_id', "")
    if user_id:
        notifications = SaleNotification.objects.filter(user_id=user_id)
        notifs_list = []
        for notification in notifications:
            response_dict = {'notif_type': notification.notif_type,
                            'id': notification.id,
                            'user_id': notification.user_id,
                            'username': notification.user_name,
                            'data': json.loads(notification.data),
                            'sale_id': notification.sale_id}
            notifs_list.append(response_dict)
        return HttpResponse(json.dumps({'response': notifs_list}), content_type="application/json")
    else:
        return HttpResponse(json.dumps({'response': 'user_id not found'}),
                            content_type="application/json")

@csrf_exempt
def delete_notification(request):
    if request.method == 'POST':
        notification_id = request.POST.get('notification_id', "")
        if notification_id:
            # delete the given notification
            if SaleNotification.objects.get(pk=int(notification_id)).delete():
                return HttpResponse(json.dumps({'response': 'true del'}),
                                    content_type="application/json")
            else:
                return HttpResponse(json.dumps({'response': 'error in deleting'}),
                                    content_type="application/json")
        else:
            return HttpResponse(json.dumps({'response': 'please send notification id'}),
                                content_type="application/json")
    else:
        return HttpResponse(json.dumps({'response': 'please send the correct request'}),
                            content_type="application/json")
@csrf_exempt
def test_patch(request):
    if request.method == 'PATCH':
        return HttpResponse('Welcome this is a patch request')
    else:
        return HttpResponse('Fuck you')

@csrf_exempt
def geo_feed_view(request):
    if request.method == 'GET':
        user_id = request.GET.get('user_id')
        latitude = float(request.GET.get('lat'))
        longitude = float(request.GET.get('long'))

        if user_id and latitude and longitude:
            current_time = datetime.now()
            user_location = Location(latitude, longitude, current_time)
            user = User.objects.get(user_id=user_id)

            feed_results = geo_feed(user, user_location)

            return HttpResponse(json.dumps(feed_results),
                                content_type="application/json")
        else:
            return HttpResponse(json.dumps({'repsonse': 'please send requied data'}),
                                content_type="application/json")

@csrf_exempt
def geo_feedv2(request):
    if request.method == 'GET':
        user_id = request.GET.get('user_id')
        latitude = float(request.GET.get('lat'))
        longitude = float(request.GET.get('long'))

        if user_id and latitude and longitude:
            current_time = datetime.now()
            user_location = Location(latitude, longitude, current_time)
            user = User.objects.get(user_id=user_id)

            geo_feed = GeoFeed(user, location)


            return HttpResponse(json.dumps(geo_feed.serialize_sales()),
                                content_type="application/json")
        else:
            return HttpResponse(json.dumps({'repsonse': 'please send requied data'}),
                                content_type="application/json")

@csrf_exempt
def sliderFeed(request):
    pass

@csrf_exempt
def hotDeals(request):
    if request.method == 'POST':
        userId = request.POST.get('user_id')
        dealsKey = userId + "_hotDeals"
        pq = MinPQ()
        pq.deserialize(dealsKey, memcache)
        if pq.size == 0:
            # make a new queue and save it
            sales = Sale.objects.all()
            for sale in sales:
                pq.enqueue(sale)
            minSale = pq.dequeue()
            pq.serialize(dealsKey, memcache)
            return HttpResponse(serializers.serialize("json", [minSale])[1:-1],
                                content_type="application/json")
        else:
            minSale = pq.dequeue()
            pq.serialize(dealsKey, memcache)
            return HttpResponse(serializers.serialize("json", [minSale])[1:-1],
                                content_type="application/json")
    else:
        return HttpResponse(json.dumps({'response': 'Only POST requests are allowed.'}),
                            content_type="application/json")

# Helper methods
@csrf_exempt
def getSaleImages(request):
    if request.method == 'POST':
        saleId = request.POST.get('sale_id')
        sale = Sale.objects.get(pk=int(saleId))
        saleImages = SaleImage.objects.filter(sale=sale)
        if saleImages:
            return HttpResponse(serializers.serialize("json", saleImages),
                                content_type="application/json")
        else:
            return HttpResponse(json.dumps({'error': 'An unknown error occured'}),
                                content_type="application/json")
    else:
        return HttpResponse(json.dumps({'error':'Please send a POST request'}),
                            content_type="application/json")

@csrf_exempt
def markSold(request):
    if request.method == 'POST':
        saleId = request.POST.get('sale_id')
        sale = Sale.objects.get(pk=saleId)
        # marking given sale as sold
        sale.sold = True
        sale.save()
        return HttpResponse(json.dumps({'response': True}),
                            content_type="application/json")
    else:
        return HttpResponse(json.dumps({'response': 'Only POST requests.'}),
                            content_type="application/json")
# END HELPER METHODS

@csrf_exempt
def placeBid(request):
    if request.method == 'POST':
        saleId = request.POST.get('sale_id')
        userId = request.POST.get('user_id')
        bidPrice = request.POST.get('bid_price')
        user = User.objects.get(user_id=userId)
        bidCacheKey = saleId + "_bid"
        if memcache.get_val(bidCacheKey) == False:
            # This is the first bid on the sale
            sale = Sale.objects.get(pk=saleId)
            # Creating a new bid from Bid Class
            bid = Bid(sale)
            bid.place_bid(user, bidPrice=bidPrice)
            if bid.serialize(memcache):
                return HttpResponse(json.dumps({'response': True}),
                                    content_type="application/json")
            else:
                return HttpResponse(json.dumps({'error': 'error bidding.'}),
                                    content_type="application/json")
        else:
            # Bid is already there now deserialize it.
            bid = Bid()
            bid.deserialize(bidCacheKey, memcache)
            bid.place_bid(user, bidPrice=bidPrice)
            if bid.serialize(memcache):
                return HttpResponse(json.dumps({'response': True}),
                                    content_type="application/json")
            else:
                return HttpResponse(json.dumps({'error': 'error bidding.'}),
                                    content_type="application/json")
    else:
        return HttpResponse(json.dumps({'response': 'Please send POST request.'}),
                            content_type="application/json")

@csrf_exempt
def bidStats(request):
    if request.method == 'POST':
        saleId = request.POST.get('sale_id')
        bidCacheKey = saleId + "_bid"
        if memcache.get_val(bidCacheKey) is not False:
            bid = Bid()
            bid.deserialize(bidCacheKey, memcache)
            return HttpResponse(json.dumps(bid.stats()),
                                content_type="application/json")
        else:
            return HttpResponse(json.dumps({'error': 'error getting stats'}),
                                content_type="application/json")
    else:
        return HttpResponse(json.dumps({'response': 'send POST request.'}),
                            content_type="application/json")

@csrf_exempt
def allSales(request):
    sales = Sale.objects.all()
    return HttpResponse(serializers.serialize("json", sales),
                        content_type="application/json")

@csrf_exempt
def getAlikeProduct(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        current_sale_id = request.POST.get('current_sale')
        userLocation = Location(request.POST.get('latitude'),
                                request.POST.get('longitude'))
        current_sale = Sale.objects.get(pk=current_sale_id)
        return HttpResponse(json.dumps({'response': true}),
                            content_type="application/json")
    else:
        return HttpResponse(json.dumps({'response':'Please send a POST request'}),
                            content_type="application/json")


################## CLASS BASED VIEWS START HERE ##################
class CreateSaleView(View):
    """ Simple cbv to create a new sale. """

    def get(self, request):
        return ServeResponse.serve_error("GET not allowed.", 403)

    def post(self, request):
        data = json.loads(request.body)
        seller_id   = data["seller_id"]
        seller_username = data["seller_username"]
        book_id = data["book_id"]
        location = data["location"]
        description = data["description"]
        price = data["price"]
        latitude = data["latitude"]
        longitude = data["longitude"]
        selected_categories = data["selected_categories"]
        geo_point = str(latitude) + "," + str(longitude)
        if book_id or book_id is 0:
            #book is not there please enter the details of the book
            #sending message back to client for uploading contents of book
            #getting the required data
            full_title = data["full_title"]
            link = ""
            uniform_title = data["uniform_title"]
            ean_13 = data["barcode_number"]
            new_book = Book.objects.create(full_title=full_title,
                                            link=link,
                                            uniform_title=uniform_title,
                                            ean_13=ean_13)
            new_book.save()
            #the book is now saved we have to save the sale and enter it in
            #the correct redis bucket for the user
            sale = Sale.objects.create(seller_id=seller_id, seller_username=seller_username,
                                book=new_book, description=description, price=price,
                                location=location, geo_point=geo_point,
                                categories=json.dumps(selected_categories))
            sale.save()
            #we have to create the images
            #front cover image
            front_cover_image = data["front_cover_image"]
            first_cover_image = data["first_cover_image"]
            back_cover_image = data["back_cover_image"]
            #saving all the sale images
            img_names = [front_cover_image, first_cover_image, back_cover_image]
            #img types
            img_types = ['front', 'first', 'back']
            imgs = zip(img_types, img_names)
            for img in imgs:
                SaleImage.objects.create(sale=sale, img_type=img[0],
                                        image_name=img[1])
            # saving this in the memcached for the required users
            memcached_response = {
                'id': sale.id, 'seller_id': sale.seller_id,
                'seller_username': sale.seller_username,
                'description': sale.description,
                'book': json.loads(serializers.serialize("json", [sale.book])[1:-1]),
                'price': sale.price,
                'location': sale.location,
                'latitude': latitude,
                'longitude': longitude,
                'images': json.loads(serializers.serialize("json",SaleImage.objects.filter(sale=sale))),
                'extra_info': sale.location
            }
            return ServeResponse.serve_response({"status": 201, "response": "sale created."}, 201)


class SaleInterestView(View):
    """ View to update a user's interest on a certain sale. """
    def get(self, request):
        return ServeResponse.serve_error("GET not allowed.", 405)

    def post(self, request):
        buyer_id = request.POST.get('buyer_id', "")
        buyer_username = request.POST.get('buyer_username', "")
        sale_id = request.POST.get('sale_id', "")
        if buyer_id and buyer_username and sale_id:
            #get the sale object and then enter it in the database
            if len(SaleInterest.objects.filter(interested_user_id=buyer_id, sale_id=sale_id)) > 0:
                return ServeResponse.serve_error("interest already exists.", 403)

            try:
                sale = Sale.objects.get(pk=sale_id)
            except ObjectDoesNotExist:
                return ServeResponse.serve_error("sale does not exist", 500)
            #creating the new sale interest object
            interest = SaleInterest.objects.create(interested_user_id=buyer_id,
                                            interested_username=buyer_username,
                                            sale=sale)
            return ServeResponse.serve_response(serializers.serialize("json", [interest])[1:-1], 201)

        return ServeResponse.serve_error("error while creating response.", 500)


class FeedView(View):
    """ Generates a personalised feed for each user. """

    def get(self, request):
        user_id = request.GET.get('user_id', "")
        assert(user_id)
        if user_id:
            try:
                user_notifications = len(SaleNotification.objects.filter(user_id=user_id))
            except (SaleNotification.DoesNotExist) as e:
                user_notifications = 0

            user = User.objects.get(user_id=user_id)
            feed = GeoFeed(user=user)

            # Memcache key
            key = sha256(user_id).hexdigest()

            # For protobuf serialization
            try:
                if int(request.GET["is_proto"]) == 1:
                    if mc.get(key) is None:
                        mc.set(key, feed.serialize_proto(), time=int(time.time() + 60))

                    return ServeResponse.serve_response(mc.get(key), 200, is_proto=True)
                
            except KeyError:
                pass

            if mc.get(key) is None:
                response = {'response': feed.serialize(),
                        'current_app_version': '1.0.1',
                        'user_notifications_number': user_notifications}
                mc.set(key, response, time=int(time.time() + 90))
                return ServeResponse.serve_response(response, 200)
            #Default response if key is available
            return ServeResponse.serve_response(mc.get(key), 200)
