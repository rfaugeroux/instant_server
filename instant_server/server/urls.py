import json
import datetime
from flask import request
from instant_server.server import app
from instant_server.db import models
from mongoengine import ValidationError
from mongoengine.queryset import DoesNotExist
from gcm import GCM
from gcm.gcm import GCMException
from apns import APNs, Payload

GCM_API_KEY = "AIzaSyCWn_dNhBHFITuVAOAG2r_KDlV5KROg-Oo"


@app.route('/send', methods=['POST'])
def send():

    #Parse the request
    content = request.form['message']
    receiver_id = request.form['to']
    sender = request.form['from']
    minutes = request.form.get('keo_time', default=0, type=int)
    photo = request.form.get('photo', default="")

    delta = datetime.timedelta(minutes=minutes)

    #Save the message in the database
    message = models.Message(sender=sender, receiver=receiver_id, 
                             content=content, photo=photo,
                             delivery_time=datetime.datetime.now() + delta, keo_time=minutes)
    message.save()
    print "Message id: " + str(message.id)

    user = models.Global_User.objects.get(email=receiver_id)

    #Handle push notifications to android and ios
    if user.reg_id and minutes < 1:
        if user.os=="android":
            gcm = GCM(GCM_API_KEY)
            data = {'sender' : sender, 'id': str(message.id), 'keo_time': str(message.keo_time)}         
            print data
            try:
                res = gcm.plaintext_request(registration_id=user.reg_id, data=data)
            except GCMException, e:
                print e
            except Exception, e:
                print e

        if user.os=="ios":
            print "Trying to send an ios push notification..."
            #apns = APNs(use_sandbox=app.debug, cert_file='KeoCert.pem', key_file='KeoKey.pem')
            apns = APNs(use_sandbox=True, cert_file='KeoCert.pem', key_file='KeoKey.pem')
            payload = Payload(alert="You got a new Keo", sound="default", badge=1)
            apns.gateway_server.send_notification(user.reg_id, payload)


    return "Message sent"

@app.route('/confirmLastUpdate', methods=['POST'])
def confirmLastUpdate():
    receiver = request.form['to']
    str_update_time = request.form['update_time']

    user_to_update = models.Global_User.objects.get(email=receiver)
    user_to_update.last_update = datetime.datetime.strptime(str_update_time, "%Y-%m-%d %H:%M:%S.%f")
    user_to_update.save()

    return "User updated"

@app.route('/receive', methods=['GET'])
def receive():
    receiver = request.args.get('to')
    #timestamp = request.args.get('timestamp')

    user = models.Global_User.objects.get(email=receiver)
    timestamp = user.last_update
    new_update_time = datetime.datetime.now()

    messages_to_receiver = []

    """Collect the messages sent to the receiver"""
    for message in models.Message.objects(receiver=receiver, delivery_time__lte=new_update_time,
                                          delivery_time__gte=timestamp):
        messages_to_receiver.append({'from': message.sender, 'message': message.content,
                                     'photo': message.photo,'created_at': str(message.created_at),
                                     'keo_time': str(message.keo_time), 'update_time': str(new_update_time)})

    return json.dumps(messages_to_receiver)

@app.route('/receive_single', methods=['GET'])
def receive_single():
    id = request.args.get('id')
    messages_to_receiver = []

    """Collect the message requested by the receiver"""
    message  = models.Message.objects.get(id=id)
    messages_to_receiver.append({'from': message.sender, 'message': message.content,
                                 'photo': message.photo, 'created_at': str(message.created_at),
                                 'keo_time': str(message.keo_time)})

    return json.dumps(messages_to_receiver)

@app.route('/delete', methods=['GET'])
def delete():
    t = datetime.timedelta(minutes=3)
    time_barrier = datetime.datetime.now() - t
    models.Message.objects(receiver="", delivery_time__lte=time_barrier).delete()
    return "Messages created more than 2 minutes ago deleted."

@app.route('/checkAccount', methods=['GET'])
def checkAccount():
    email = request.args.get('email')
    if models.Global_User.objects(email=email):
        return 'existe_deja'
    else:
        return 'continue'

@app.route('/signup', methods=['POST'])
def signup():
    email = request.form['email']
    password = request.form['password']
    phone_number = request.form['phone_number']
    os = request.form['os']
    reg_id = request.form.get('reg_id', default=None)

    if models.Global_User.objects(email=email):
        return "existe_deja"

    try:
        new_user = models.Global_User(email=email, phone_number=phone_number, password=password, os=os, reg_id=reg_id)
        new_user.save(validate=False)
        return "cree"

    except ValidationError, e:
        print e

    return "pas_cree"

@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']
    os = request.form['os']
    reg_id = request.form.get('reg_id', default=None)

    try:
        user = models.User.objects.get(email=email, password=password)
        user.os = os
        if reg_id:
            user.reg_id = reg_id
        user.save()

        return user.phone_number
    
    except DoesNotExist:
        return "DoesNotExist"
         
    return "NTM"

@app.route('/sendRegId', methods=['POST'])
def sendRegId():
    reg_id = request.form['reg_id']


@app.route('/users', methods=['GET'])
def get_users():
    users = []
    for user in models.Global_User.objects:
        users.append({'email': user.email, 'phone number': user.phone_number, 'password': "*******"})
    return json.dumps(users)


@app.route('/hello')
def hello_world():
    return 'Hello Hello'

