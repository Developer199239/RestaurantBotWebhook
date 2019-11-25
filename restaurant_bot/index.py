from flask import Flask, request, jsonify, render_template
import os
import dialogflow
import requests
import json
import pusher
import time

app = Flask(__name__)

user_info_dic = {}
tacos_food_order = {}
user_delivery_type = {}

# initialize Pusher
pusher_client = pusher.Pusher(
    app_id=os.getenv('PUSHER_APP_ID'),
    key=os.getenv('PUSHER_KEY'),
    secret=os.getenv('PUSHER_SECRET'),
    cluster=os.getenv('PUSHER_CLUSTER'),
    ssl=True)

# Intent constants
INTENT_FOOD_CATEGORY = "food.category"
INTENT_MOVIE = "movie"

DEBUG_LOG_ENABLE = True


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/restaurant_bot_api', methods=['POST'])
def restaurant_bot_api():
    data = request.get_json(silent=True)
    print("============= start ========")
    print(data)
    print("============= end ========")
    try:

        # length = len(user_info_dic)
        # print(f"{length}")
        # length = length + 1
        # millis = int(round(time.time() * 1000))
        # user = UserModel(length, millis)
        # user_info_dic[length] = user
        platform = get_request_platform_source(data)
        response = process_for_facebook(data)
        return jsonify(response)
        # if platform == "facebook":
        #     response = process_for_facebook(data)
        #     return jsonify(response)
        # else:
        #     response = "from console"
        #     reply = {"fulfillmentText": response}
        #     return jsonify(reply)
    except Exception as e:
        response = f"error block {e}"
        reply = {"fulfillmentText": response}
        return jsonify(reply)


def detect_intent_texts(project_id, session_id, text, language_code):
    session_client = dialogflow.SessionsClient()
    session = session_client.session_path(project_id, session_id)

    if text:
        text_input = dialogflow.types.TextInput(
            text=text, language_code=language_code)
        query_input = dialogflow.types.QueryInput(text=text_input)
        response = session_client.detect_intent(
            session=session, query_input=query_input)

        return response.query_result.fulfillment_text


@app.route('/send_message', methods=['POST'])
def send_message():
    try:
        socketId = request.form['socketId']
    except KeyError:
        socketId = ''

    message = request.form['message']
    project_id = os.getenv('DIALOGFLOW_PROJECT_ID')
    fulfillment_text = detect_intent_texts(project_id, "unique", message, 'en')
    response_text = {"message": fulfillment_text}

    pusher_client.trigger(
        'movie_bot',
        'new_message',
        {
            'human_message': message,
            'bot_message': fulfillment_text,
        },
        socketId
    )

    return jsonify(response_text)


def process_for_facebook(data):
    # get action from json
    action = data['queryResult']['action']
    if action == "food.category":
        food_type = data['queryResult']['parameters']['food_type']
        sender_id = get_facebook_sender_id(data)
        last_update = int(round(time.time() * 1000))
        if sender_id in user_info_dic:
            user = user_info_dic[sender_id]
            user.last_update = last_update
            user.current_food_category = food_type
        else:
            user = UserModel()
            user.user_id = sender_id
            user.last_update = last_update
            user.current_food_category = food_type
            user_info_dic[sender_id] = user

        if DEBUG_LOG_ENABLE:
            for x in user_info_dic.values():
                print(x.current_food_category)

        if str(food_type).lower() == "Bangladeshi".lower():
            fulfillment_text = 'bangladeshi food category'
            ff_response = FulfillmentResponse()
            fulfillment_message = ff_response.fulfillment_text(fulfillment_text)

            fb_platform = FacebookResponse()
            title = ['Please choose a Category:']
            text_res = fb_platform.text_response(title)

            tacos_buttons = [
                ['Show More', 'show tacos item']
            ]
            card1 = fb_platform.make_card_response("Tacos", "Tacos is popular food item",
                                                   "http://jalilurrahman.com/ChatBotImageResource/tacos1.jpeg",
                                                   tacos_buttons)

            pizza_buttons = [
                ['Show More', 'show Pizza Item']
            ]
            card2 = fb_platform.make_card_response("Pizza", "Pizza is most popular food item",
                                                   "http://jalilurrahman.com/ChatBotImageResource/mexican_pizza_2.jpeg",
                                                   pizza_buttons)
            burger_buttons = [
                ['Show More', 'show Burger Item']
            ]
            card3 = fb_platform.make_card_response("Burger", "Burger is popular food item",
                                                   "http://jalilurrahman.com/ChatBotImageResource/burger1.jpeg",
                                                   burger_buttons)
            card_response = fb_platform.card_full_fillment([text_res, card1, card2, card3])

            reply = ff_response.main_response(fulfillment_message, card_response)
            if DEBUG_LOG_ENABLE:
                print(reply)
            return reply
        elif str(food_type).lower() == "Mexicun".lower():
            fulfillment_text = 'Mexicun food category'
            ff_response = FulfillmentResponse()
            fulfillment_message = ff_response.fulfillment_text(fulfillment_text)

            fb_platform = FacebookResponse()
            title = ['Please choose a Category:']
            text_res = fb_platform.text_response(title)

            tacos_buttons = [
                ['Show More', 'show tacos item']
            ]
            card1 = fb_platform.make_card_response("Tacos", "Tacos is popular food item",
                                                   "http://jalilurrahman.com/ChatBotImageResource/tacos1.jpeg",
                                                   tacos_buttons)

            pizza_buttons = [
                ['Show More', 'show Pizza Item']
            ]
            card2 = fb_platform.make_card_response("Pizza", "Pizza is most popular food item",
                                                   "http://jalilurrahman.com/ChatBotImageResource/mexican_food.jpeg",
                                                   pizza_buttons)
            burger_buttons = [
                ['Show More', 'show Burger Item']
            ]
            card3 = fb_platform.make_card_response("Burger", "Burger is popular food item",
                                                   "http://jalilurrahman.com/ChatBotImageResource/burger1.jpeg",
                                                   burger_buttons)
            card_response = fb_platform.card_full_fillment([text_res, card1, card2, card3])

            reply = ff_response.main_response(fulfillment_message, card_response)
            if DEBUG_LOG_ENABLE:
                print(reply)
            return reply
    elif action == "food.category.order":
        sender_id = get_facebook_sender_id(data)
        update_user_last_trigger_time(sender_id)
        food_category = get_food_category(sender_id)
        food_category_order = data['queryResult']['parameters']['food_category']

        if str(food_category_order).lower() == "tacos":
            return process_food_order_tacos(food_category)
        elif str(food_category_order).lower() == "pizza":
            pass
        elif str(food_category_order).lower() == "burger":
            pass
    elif action == "food.category.order.items":
        sender_id = get_facebook_sender_id(data)
        update_user_last_trigger_time(sender_id)

        food_category = ""  # tacos, burger, pizza
        output_contexs = data['queryResult']['outputContexts']
        for row in output_contexs:
            if "parameters" in row:
                parameters = row['parameters']
                if "food_category" in parameters:
                    food_category = str(parameters['food_category'])
                    break
        order_food_items = data['queryResult']['parameters']['order_food_items']  # bangladeshi tacos 1, mexicun....

        food_category_type = get_food_category(sender_id)  # bnagladeshi or mexicun

        if food_category == "tacos":
            return process_food_order_tacos_booking(sender_id, order_food_items, food_category_type)
        elif food_category == "pizza":
            pass
        elif food_category == "burger":
            pass
    elif action == "order.quantity":
        if DEBUG_LOG_ENABLE:
            print("#########")
            print(data)

        sender_id = get_facebook_sender_id(data)
        update_user_last_trigger_time(sender_id)

        food_category = ""  # tacos, burger, pizza
        order_food_items = ""  # bangladeshi tacos 1,....
        output_contexs = data['queryResult']['outputContexts']
        for row in output_contexs:
            if "parameters" in row:
                parameters = row['parameters']
                if "food_category" in parameters:
                    food_category = str(parameters['food_category'])
                    order_food_items = str(parameters['order_food_items'])
                    break
        order_quantity_number = data['queryResult']['parameters'][
            'order_quantity_number']  # 1, 2, 3... order quantity number

        if food_category == "tacos":
            return process_food_order_tacos_quantity(sender_id, food_category, order_food_items, order_quantity_number)
        elif food_category == "pizza":
            pass
        elif food_category == "burger":
            pass
    elif action == "show.cart":
        sender_id = get_facebook_sender_id(data)
        update_user_last_trigger_time(sender_id)
        return show_my_cart(sender_id)
    elif action == "cart.remove":
        sender_id = get_facebook_sender_id(data)
        update_user_last_trigger_time(sender_id)
        remove_cart_item = data['queryResult']['parameters']['remove_cart_item']
        food_category = data['queryResult']['parameters']['food_category']
        return remove_my_cart(sender_id, remove_cart_item, food_category)
    elif action == "place.order":
        return place_order()
    elif action == "place.order.on.table":
        sender_id = get_facebook_sender_id(data)
        update_user_last_trigger_time(sender_id)
        return place_order_on_table(sender_id)
    elif action == "place.order.on.table.number":
        sender_id = get_facebook_sender_id(data)
        update_user_last_trigger_time(sender_id)
        msg = "You have chosen on table order. Please, click checkout to proceed to payment. You can edit also your " \
              "cart content or delivery method from the option given below "
        return confirm_order_message(sender_id, msg)
    elif action == "order.confirm":
        sender_id = get_facebook_sender_id(data)
        update_user_last_trigger_time(sender_id)
        return confirm_order(sender_id)
    else:
        return "nothing"


# confirm order
def confirm_order(sender_id):
    fulfillment_text = 'confirm order'
    ff_response = FulfillmentResponse()
    fulfillment_message = ff_response.fulfillment_text(fulfillment_text)

    fb_platform = FacebookResponse()
    fb_quick_replies = fb_platform.text_response("need to open website")

    ff_response = FulfillmentResponse()
    quick_replies_response = {
        "fulfillment_messages": [
            {
                "payload": {
                    "facebook": {
                        "attachment": {
                            "type": "template",
                            "payload": {
                                "template_type": "button",
                                "text": "Try the URL button!",
                                "buttons": [
                                    {
                                        "type": "web_url",
                                        "url": "https://www.messenger.com/",
                                        "title": "URL Button",
                                        "webview_height_ratio": "tall"
                                    }
                                ]
                            }
                        }
                    }
                }
            }
        ]
    }

    reply = ff_response.main_response(fulfillment_message, quick_replies_response)
    if DEBUG_LOG_ENABLE:
        print(reply)
    return reply


def confirm_order_message(sender_id, msg):
    fulfillment_text = 'confirm order'
    ff_response = FulfillmentResponse()
    fulfillment_message = ff_response.fulfillment_text(fulfillment_text)

    fb_platform = FacebookResponse()
    replies = ['Confirm Order', 'Edit Cart', 'Edit Delivery']
    fb_quick_replies = fb_platform.quick_replies(msg, replies)

    ff_response = FulfillmentResponse()
    quick_replies_response = ff_response.fulfillment_messages([fb_quick_replies])
    reply = ff_response.main_response(fulfillment_message, quick_replies_response)
    if DEBUG_LOG_ENABLE:
        print(reply)
    return reply


# Place order on table
def place_order_on_table(sender_id):
    fulfillment_text = 'Place order on table'
    ff_response = FulfillmentResponse()
    fulfillment_message = ff_response.fulfillment_text(fulfillment_text)

    user_delivery_type[sender_id] = "on_table"
    fb_platform = FacebookResponse()
    fb_text_response = fb_platform.text_response(['Please type your table number'])
    ff_response = FulfillmentResponse()
    quick_replies_response = ff_response.fulfillment_messages([fb_text_response])
    reply = ff_response.main_response(fulfillment_message, quick_replies_response)
    if DEBUG_LOG_ENABLE:
        print(reply)
    return reply


# Place Order
def place_order():
    fulfillment_text = 'Place order'
    ff_response = FulfillmentResponse()
    fulfillment_message = ff_response.fulfillment_text(fulfillment_text)

    fb_platform = FacebookResponse()
    title = "Please, choose a delivery method:"
    replies = ['On Table', 'Delivery', 'Pickup']
    fb_quick_replies = fb_platform.quick_replies(title, replies)

    ff_response = FulfillmentResponse()
    quick_replies_response = ff_response.fulfillment_messages([fb_quick_replies])
    reply = ff_response.main_response(fulfillment_message, quick_replies_response)
    if DEBUG_LOG_ENABLE:
        print(reply)
    return reply


# my cart
def remove_my_cart(sender_id, remove_cart_item, food_category):
    if str(food_category).lower() == "tacos".lower():
        my_tacos_items = []
        update_tacos_items = []
        if sender_id in tacos_food_order:
            my_tacos_items = tacos_food_order[sender_id]
            for row in my_tacos_items:
                if str(row['item_name']).lower() != str(remove_cart_item).lower():
                    update_tacos_items.append(row)
        if len(update_tacos_items) == 0:
            tacos_food_order.pop(sender_id)
        else:
            tacos_food_order[sender_id] = update_tacos_items

    return show_my_cart(sender_id)


def show_my_cart(sender_id):
    # Tacos food order
    my_tacos_order = []
    if sender_id in tacos_food_order:
        my_tacos_order = tacos_food_order[sender_id]

    #  check my cart empty
    is_empty_my_cart = False
    if len(my_tacos_order) == 0:
        is_empty_my_cart = True

    if is_empty_my_cart:
        #  todo show my food category
        fulfillment_text = 'empty my cart list'
        ff_response = FulfillmentResponse()
        fulfillment_message = ff_response.fulfillment_text(fulfillment_text)

        fb_platform = FacebookResponse()
        fb_text_replay = fb_platform.text_response(['Empty my cart list'])

        ff_response = FulfillmentResponse()

        quick_replies_response = ff_response.fulfillment_messages([fb_text_replay])
        reply = ff_response.main_response(fulfillment_message, quick_replies_response)
        if DEBUG_LOG_ENABLE:
            print(reply)
        return reply
    else:
        bangladeshi_tacos_1_item = 0
        bangladeshi_tacos_2_item = 0
        bangladeshi_tacos_3_item = 0

        print("====show my cart====")
        print(my_tacos_order)

        for row in my_tacos_order:
            if bool(row['status']):
                if str(row['item_name']) == "bangladeshi tacos 1":
                    bangladeshi_tacos_1_item = bangladeshi_tacos_1_item + int(row['quantity'])
                    print("bangladeshi_tacos_1_item " + str(bangladeshi_tacos_1_item))
                elif str(row['item_name']) == "bangladeshi tacos 2":
                    bangladeshi_tacos_2_item = bangladeshi_tacos_2_item + int(row['quantity'])
                    print("bangladeshi_tacos_2_item " + str(bangladeshi_tacos_2_item))
                elif str(row['item_name']) == "bangladeshi tacos 3":
                    bangladeshi_tacos_3_item = bangladeshi_tacos_3_item + int(row['quantity'])
                    print("bangladeshi_tacos_3_item " + str(bangladeshi_tacos_3_item))

        #  process response
        fulfillment_text = 'process order'
        ff_response = FulfillmentResponse()
        fulfillment_message = ff_response.fulfillment_text(fulfillment_text)

        fb_cart_order_response = []
        fb_platform = FacebookResponse()

        if bangladeshi_tacos_1_item > 0:
            cart_title = str("bangladeshi tacos 1").title()
            cart_sub_title = "Price " + str(bangladeshi_tacos_1_item * 5) + "$, Quantity: " + str(
                bangladeshi_tacos_1_item)
            call_back_text_place_order = "Place Order"  # intent
            call_back_text_change_quantity = "change quantity bangladeshi tacos 1"  # todo need to intent
            call_back_text_remove_from_cart = "remove from cart bangladeshi tacos 1 and food category tacos"  # todo need to intent
            tacos_buttons = [
                ['Place Order', call_back_text_place_order],
                ['Change Quantity', call_back_text_change_quantity],
                ['Remove From Cart', call_back_text_remove_from_cart]
            ]
            tacos = fb_platform.make_card_response(cart_title, cart_sub_title,
                                                   "http://jalilurrahman.com/ChatBotImageResource/tacos1.jpeg",
                                                   tacos_buttons)
            fb_cart_order_response.append(tacos)

        if bangladeshi_tacos_2_item > 0:
            cart_title = str("bangladeshi tacos 2").title()
            cart_sub_title = "Price " + str(bangladeshi_tacos_2_item * 7) + "$, Quantity: " + str(
                bangladeshi_tacos_2_item)
            call_back_text_place_order = "Place Order"  # intent
            call_back_text_change_quantity = "change quantity bangladeshi tacos 2"  # todo need to intent
            call_back_text_remove_from_cart = "remove from cart bangladeshi tacos 2 and food category tacos"  # todo need to intent
            tacos_buttons = [
                ['Place Order', call_back_text_place_order],
                ['Change Quantity', call_back_text_change_quantity],
                ['Remove From Cart', call_back_text_remove_from_cart]
            ]
            tacos = fb_platform.make_card_response(cart_title, cart_sub_title,
                                                   "http://jalilurrahman.com/ChatBotImageResource/tacos2.jpeg",
                                                   tacos_buttons)
            fb_cart_order_response.append(tacos)
        if bangladeshi_tacos_3_item > 0:
            cart_title = str("bangladeshi tacos 3").title()
            cart_sub_title = "Price " + str(bangladeshi_tacos_3_item * 10) + "$, Quantity: " + str(
                bangladeshi_tacos_3_item)
            call_back_text_place_order = "Place Order"  # intent
            call_back_text_change_quantity = "change quantity bangladeshi tacos 3"  # todo need to intent
            call_back_text_remove_from_cart = "remove from cart bangladeshi tacos 3 and food category tacos"  # todo need to intent
            tacos_buttons = [
                ['Place Order', call_back_text_place_order],
                ['Change Quantity', call_back_text_change_quantity],
                ['Remove From Cart', call_back_text_remove_from_cart]
            ]
            tacos = fb_platform.make_card_response(cart_title, cart_sub_title,
                                                   "http://jalilurrahman.com/ChatBotImageResource/tacos3.jpeg",
                                                   tacos_buttons)
            fb_cart_order_response.append(tacos)

        print(f"{len(fb_cart_order_response)}")
        print(fb_cart_order_response)

        # todo check order list is empty
        # process facebook response
        final_response = fb_platform.card_full_fillment(fb_cart_order_response)
        reply = ff_response.main_response(fulfillment_message, final_response)
        if DEBUG_LOG_ENABLE:
            print(reply)
        return reply


# Food category order
def process_food_order_tacos_quantity(sender_id, food_category, order_food_items, order_quantity_number):
    # here sender_id = user facebook id
    # food_category = ""  # tacos, burger, pizza
    # order_food_items = ""  # bangladeshi tacos 1,....
    # order_quantity_number = 1,2,3,4...
    user_tacos_order = []
    if sender_id in tacos_food_order:
        user_tacos_order = tacos_food_order[sender_id]

    for row in user_tacos_order:
        if not bool(row['status']):
            row['status'] = True
            row['quantity'] = int(order_quantity_number)
            break

    tacos_food_order[sender_id] = user_tacos_order
    fulfillment_text = 'process food order tacos quantity'
    ff_response = FulfillmentResponse()
    fulfillment_message = ff_response.fulfillment_text(fulfillment_text)

    fb_platform = FacebookResponse()
    text_title = "Quantity of" + str(food_category).title() + " " + str(
        order_food_items).title() + " has been update to " + str(order_quantity_number) + "."
    text_res = fb_platform.text_response([text_title])

    quick_replay_title = "Would you like to continue shopping?"
    replies = ['Yes, Continue', 'Place Order', 'Show Cart']
    fb_quick_replies = fb_platform.quick_replies(quick_replay_title, replies)

    ff_response = FulfillmentResponse()

    quick_replies_response = ff_response.fulfillment_messages([text_res, fb_quick_replies])
    reply = ff_response.main_response(fulfillment_message, quick_replies_response)

    if DEBUG_LOG_ENABLE:
        print("==== order process ===")
        if sender_id in tacos_food_order:
            user_tacos_order = tacos_food_order[sender_id]

        for row in user_tacos_order:
            print(row['item_name'])
            print(row['price'])
            print(row['quantity'])
            print(row['status'])

    if DEBUG_LOG_ENABLE:
        print(reply)
    return reply


def process_food_order_tacos_booking(sender_id, order_food_items, food_category_type):
    # update tacos order
    user_tacos_order = []
    if sender_id in tacos_food_order:
        user_tacos_order = tacos_food_order[sender_id]

    # remove item which are status false
    for row in user_tacos_order:
        if not bool(row['status']):
            user_tacos_order.remove(row)

    if order_food_items == "bangladeshi tacos 1":
        new_tacos_order = {
            "item_name": str(order_food_items),
            "price": 5,
            "quantity": 0,
            "status": False
        }
        user_tacos_order.append(new_tacos_order)
        tacos_food_order[sender_id] = user_tacos_order
    elif order_food_items == "bangladeshi tacos 2":
        new_tacos_order = {
            "item_name": str(order_food_items),
            "price": 7,
            "quantity": 0,
            "status": False
        }
        user_tacos_order.append(new_tacos_order)
        tacos_food_order[sender_id] = user_tacos_order
    elif order_food_items == "bangladeshi tacos 3":
        new_tacos_order = {
            "item_name": str(order_food_items),
            "price": 10,
            "quantity": 0,
            "status": False
        }
        user_tacos_order.append(new_tacos_order)
        tacos_food_order[sender_id] = user_tacos_order

    fulfillment_text = 'Mexicun food category'
    ff_response = FulfillmentResponse()
    fulfillment_message = ff_response.fulfillment_text(fulfillment_text)

    fb_platform = FacebookResponse()
    title = "How many items of " + str(food_category_type).title() + " Tacos do you need?"
    replies = ['1', '2', '3', '4', '5', '6', '7']
    fb_quick_replies = fb_platform.quick_replies(title, replies)

    ff_response = FulfillmentResponse()

    quick_replies_response = ff_response.fulfillment_messages([fb_quick_replies])
    reply = ff_response.main_response(fulfillment_message, quick_replies_response)
    if DEBUG_LOG_ENABLE:
        print(reply)
    return reply


def process_food_order_tacos(food_category):
    fulfillment_text = 'tacos food category'
    ff_response = FulfillmentResponse()
    fulfillment_message = ff_response.fulfillment_text(fulfillment_text)

    fb_platform = FacebookResponse()
    call_back_text = "select " + str(food_category).lower() + " tacos 1"
    tacos_buttons = [
        ['Add to cart', call_back_text]
    ]
    title = str(food_category).title() + " Tacos1"
    tacos1 = fb_platform.make_card_response(title, "5$",
                                            "http://jalilurrahman.com/ChatBotImageResource/tacos1.jpeg",
                                            tacos_buttons)
    call_back_text = "select " + str(food_category).lower() + " tacos 2"
    tacos_buttons = [
        ['Add to cart', call_back_text]
    ]
    title = str(food_category).title() + " Tacos2"
    tacos2 = fb_platform.make_card_response(title, "7$",
                                            "http://jalilurrahman.com/ChatBotImageResource/tacos2.jpeg",
                                            tacos_buttons)

    call_back_text = "select " + str(food_category).lower() + " tacos 3"
    tacos_buttons = [
        ['Add to cart', call_back_text]
    ]
    title = str(food_category).title() + " Tacos3"
    tacos3 = fb_platform.make_card_response(title, "10$",
                                            "http://jalilurrahman.com/ChatBotImageResource/tacos3.jpeg",
                                            tacos_buttons)
    tacos_response = fb_platform.card_full_fillment([tacos1, tacos2, tacos3])

    reply = ff_response.main_response(fulfillment_message, tacos_response)
    if DEBUG_LOG_ENABLE:
        print(reply)
    return reply


# Helper method
def update_user_last_trigger_time(facebook_sender_id):
    last_update = int(round(time.time() * 1000))
    if facebook_sender_id in user_info_dic:
        user = user_info_dic[facebook_sender_id]
        user.last_update = last_update


def get_food_category(facebook_sender_id):
    print(user_info_dic)
    if facebook_sender_id in user_info_dic:
        user = user_info_dic[facebook_sender_id]
        return user.current_food_category
    else:
        return ""


def get_request_platform_source(data):
    if "source" in data['originalDetectIntentRequest']:
        return data['originalDetectIntentRequest']['source']
    else:
        return "console"


def get_facebook_sender_id(data):
    return data['originalDetectIntentRequest']['payload']['data']['sender']['id']


class ActionsOnGoogleResponse:

    # class variable initializer initializer
    def __init__(self):
        self.platform = "ACTIONS_ON_GOOGLE"

    """
    Actions on Google Simple Response Builder
    @param name=display_text, type=list
    Sample example of display_text ex. [["Text to be displayed", "Text to  be spoken", True]]
    """

    def simple_response(self, responses):

        if len(responses) > 2:
            raise Exception(
                "Responses argument in simple response should have at most two elements only.")
        else:
            # a list to store the responses
            responses_json = []
            # iterate through the list of responses given by the user
            for response in responses:
                # if SSML = True, build the ssml response, else build textToSpeech
                # response[2] = SSML boolean
                if response[2]:
                    # response dictionary
                    response_dict = {
                        # text to be diplayed
                        "displayText": str(response[0]),
                        # ssml response to be spoken
                        "ssml": str(response[1])
                    }
                else:
                    response_dict = {
                        # text to be displayed
                        "displayText": str(response[0]),
                        # text to speech text
                        "textToSpeech": str(response[1])
                    }

                # add the response dict to the responses list
                responses_json.append(response_dict)

            # return the simple response JSON
            return {
                "platform": self.platform,
                "simpleResponses": {
                    "simpleResponses": responses_json
                }
            }

    """"
    Actions on Google Basic Card Builder
    @param title = string
    @param subtitle = string
    @param formattedText = string
    @param image = list [image_url, accessibility_text]
    @param buttons = list of [button_title, url_link]
    """

    def basic_card(self, title, subtitle="", formattedText="", image=None, buttons=None):
        # list to store buttons responses
        buttons_json = []
        if buttons is not None:
            # iterate through the buttons list
            for button in buttons:
                # add the buttons response to the buttons list
                buttons_json.append(
                    {
                        # title of the button
                        "title": button[0],
                        # url to be opened by the button
                        "openUriAction": {
                            "uri": button[1]
                        }
                    }
                )

            # return basic card JSON
            response = {
                "platform": self.platform,
                "basicCard": {
                    "title": title,
                    "subtitle": subtitle,
                    "formattedText": formattedText,
                    "buttons": buttons_json,
                    "image": {
                        "imageUri": image[0],
                        "accessibilityText": image[1]
                    }
                }
            }

        else:
            # return basic card JSON
            response = {
                "platform": self.platform,
                "basicCard": {
                    "title": title,
                    "subtitle": subtitle,
                    "formattedText": formattedText,
                    "image": {
                        "imageUri": image[0],
                        "accessibilityText": image[1]
                    }
                }
            }

        return response

    """
    Actions on Google List response
    @param list_title = string
    @param list_elements = list of list response items
    """

    def list_select(self, list_title, list_elements):
        # as per the actions on google response list items must be between 2 and 30
        if len(list_elements) > 30 or len(list_elements) < 2:
            raise Exception("List items must be two or less than 30.")
        else:
            # items list to store list elements
            items_list = []
            # iterate through the list elements list
            for list_element in list_elements:
                # append the items to the items_list
                items_list.append(
                    {
                        # title of the list item
                        "title": list_element[0],
                        # description of the list item
                        "description": list_element[1],
                        # info aabout the list item
                        "info": {
                            # key of the list items, key is used as user say string
                            "key": list_element[2][0],
                            # synonyms are the words that can be used as a value for the option when the user types instead of selecting from the list
                            "synonyms": list_element[2][1]
                        },
                        # list image
                        "image": {
                            # URL
                            "imageUri": list_element[3][0],
                            # accessibility text to be spoken
                            "accessibilityText": list_element[3][1]
                        }
                    }
                )

        # return the list response
        return {
            "platform": self.platform,
            "listSelect": {
                "title": list_title,
                "items": items_list
            }
        }

    """
    Actions on Google Suggestions chips resoponse
    @param suggestions = list of strings
    """

    def suggestion_chips(self, suggestions):
        # suggestions_json to store the suggestions JSON
        suggestions_json = []
        # iterate through the suggestions list
        for suggestion in suggestions:
            # append the suggestion to the suggestions_json list
            suggestions_json.append(
                {
                    # title text to be displayed in the chip
                    "title": str(suggestion)
                }
            )

        # return the suggestion chips response JSON
        return {
            "platform": self.platform,
            "suggestions": {
                "suggestions": suggestions_json
            }
        }

    """
    Actions on Google Linkout suggestions
    @param title = string
    @param url = string (a valid URL)
    """

    def link_out_suggestion(self, title, url):
        # title should not be null
        if title == "" or url == "":
            raise Exception(
                "Provide the title and URL for link out suggestion response.")
        else:
            # return the link out suggestion response
            return {
                "platform": self.platform,
                "linkOutSuggestion": {
                    "destinationName": str(title),
                    "uri": str(url)
                }
            }


# Responses for Facebook
class FacebookResponse:

    # class variable initializer initializer
    def __init__(self):
        self.platform = "FACEBOOK"

    def text_response(self, texts):
        # text should contain at least one string
        if len(texts) <= 0:
            raise Exception("Provide the text for the text response")
        else:
            # text_obj list for storing the text variations
            text_obj = []
            for text in texts:
                text_obj.append(str(text))

            # return the text response
            return {
                "text": {
                    "text": text_obj
                },
                "platform": self.platform
            }

    def quick_replies(self, title, quick_replies_list):
        if title == "":
            raise Exception("Title is required for basic card in facebook.")
        # quick_replies_list must contains at least one string
        elif len(quick_replies_list) <= 0:
            raise Exception(
                "Quick replies response must contain at least on text string.")
        else:
            # quick replies list to store the quick replie text
            quick_replies = []
            for quick_reply in quick_replies_list:
                # append to the list
                quick_replies.append(
                    str(quick_reply)
                )

            # return the response JSON
            return {
                "quickReplies": {
                    "title": str(title),
                    "quickReplies": quick_replies
                },
                "platform": self.platform
            }

    def image_response(self, url):
        # check url
        if url == "":
            raise Exception("URL in the image response is required.")
        else:
            # return the JSON response
            return {
                "image": {
                    "imageUri": str(url)
                },
                "platform": self.platform
            }

    def card_response(self, title, buttons):
        buttons_json = []
        for button in buttons:
            buttons_json.append(
                {
                    "text": str(button[0]),
                    "postback": str(button[1])
                }
            )

        # return the card
        return {
            "card": {
                "title": str(title),
                "buttons": buttons_json
            },
            "platform": self.platform
        }

    def make_card_response(self, title, subtitle, image_uri, buttons):
        buttons_json = []
        for button in buttons:
            buttons_json.append(
                {
                    "text": str(button[0]),
                    "postback": str(button[1])
                }
            )
        response_dict = {
            "card": {
                "title": str(title),
                "subtitle": str(subtitle),
                "imageUri": image_uri,
                "buttons": buttons_json
            },
            "platform": self.platform
        }
        return response_dict

    def card_full_fillment(self, cards):
        card_respons = []
        for card in cards:
            card_respons.append(card)

        response = {'fulfillment_messages': card_respons}
        return response

    def card_advance_response(self):
        responses_json = []
        response_dict = {
            "card": {
                "title": str("Welcome to Roncom Restaurant."),
                "subtitle": str("Flavorful broths can enhance a wide range of trendy dishes while saving on labor."),
                "imageUri": "http://jalilurrahman.com/ChatBotImageResource/cover.jpeg",
                "buttons": [
                    {
                        "text": "Food Menu",
                        "postback": "show food menu"
                    }
                ]
            },
            "platform": self.platform
        }

        response_dict2 = {
            "card": {
                "title": str("Welcome to Roncom Restaurant."),
                "subtitle": str("Flavorful broths can enhance a wide range of trendy dishes while saving on labor."),
                "imageUri": "http://jalilurrahman.com/ChatBotImageResource/cover.jpeg",
                "buttons": [
                    {
                        "text": "Food Menu",
                        "postback": "show food menu"
                    }
                ]
            },
            "platform": self.platform
        }
        responses_json.append(response_dict)
        responses_json.append(response_dict2)
        response = {'fulfillment_messages': responses_json}
        return response

    def custom_payload(self, payload):

        # return custom payload
        return {
            "payload": payload,
            "platform": self.platform
        }


# Responses for Telegram
class TelegramResponse:

    # class variable initializer initializer
    def __init__(self):
        self.platform = "TELEGRAM"

    def text_response(self, texts):
        # text should contain at least one string
        if len(texts) <= 0:
            raise Exception("Provide the text for the text response")
        else:
            # text_obj list for storing the text variations
            text_obj = []
            for text in texts:
                text_obj.append(str(text))

            # return the text response
            return {
                "text": {
                    "text": text_obj
                },
                "platform": self.platform
            }

    def quick_replies(self, title, quick_replies_list):
        if title == "":
            raise Exception("Title is required for basic card in facebook.")
        # quick_replies_list must contains at least one string
        elif len(quick_replies_list) <= 0:
            raise Exception(
                "Quick replies response must contain at least on text string.")
        else:
            # quick replies list to store the quick replie text
            quick_replies = []
            for quick_reply in quick_replies_list:
                # append to the list
                quick_replies.append(
                    str(quick_reply)
                )

            # return the response JSON
            return {
                "quickReplies": {
                    "title": str(title),
                    "quickReplies": quick_replies
                },
                "platform": self.platform
            }

    def image_response(self, url):
        # check url
        if url == "":
            raise Exception("URL in the image response is required.")
        else:
            # return the JSON response
            return {
                "image": {
                    "imageUri": str(url)
                },
                "platform": self.platform
            }

    def card_response(self, title, buttons):
        buttons_json = []
        for button in buttons:
            buttons_json.append(
                {
                    "text": str(button[0]),
                    "postback": str(button[1])
                }
            )

        return {
            "card": {
                "title": str(title),
                "buttons": buttons_json
            },
            "platform": self.platform
        }


# dialogflow fulfillment response
class FulfillmentResponse:

    def __init__(self):
        pass

    # fulfillment text builder
    # @param fulfillmentText = string
    def fulfillment_text(self, fulfillmentText):
        if fulfillmentText == "":
            raise Exception("Fulfillment text should not be empty.")
        else:
            return {
                "fulfillment_text": str(fulfillmentText)
            }

    # fulfillment messages builder
    # @param response_objects (AOG response, FB response, Telegram response)
    def fulfillment_messages(self, response_objects):
        if len(response_objects) <= 0:
            raise Exception(
                "Response objects must contain at least one response object.")
        else:
            return {
                "fulfillment_messages": response_objects
            }

    # dialogflow output contexts
    # @param session = dialogflow session id
    # @param contexts = context name (string)
    def output_contexts(self, session, contexts):
        contexts_json = []
        for context in contexts:
            contexts_json.append({
                "name": session + "/contexts/" + context[0],
                "lifespanCount": context[1],
                "parameters": context[2]
            })

        # return the output context json
        return {
            "output_contexts": contexts_json
        }

    # dialogflow followup event JSON
    # @param name = event name
    # @param parameters = key value pair of parameters to be passed
    def followup_event_input(self, name, parameters):
        return {
            "followup_event_input": {
                "name": str(name),
                "parameters": parameters
            }
        }

    # main response with fulfillment text and fulfillment messages
    # @param fulfillment_text = fulfillment_text JSON
    # @param fulfillment_messages = fulfillment_messages JSON
    # @param output_contexts = output_contexts JSON
    # @param followup_event_input = followup_event_input JSON
    def main_response(self, fulfillment_text, fulfillment_messages=None, output_contexts=None,
                      followup_event_input=None):
        if followup_event_input is not None:
            if output_contexts is not None:
                if fulfillment_messages is not None:
                    response = {
                        "fulfillmentText": fulfillment_text['fulfillment_text'],
                        "fulfillmentMessages": fulfillment_messages['fulfillment_messages'],
                        "outputContexts": output_contexts['output_contexts'],
                        "followupEventInput": followup_event_input['followup_event_input']
                    }
                else:
                    response = {
                        "fulfillmentText": fulfillment_text['fulfillment_text'],
                        "outputContexts": output_contexts['output_contexts'],
                        "followupEventInput": followup_event_input['followup_event_input']
                    }
            else:
                if fulfillment_messages is not None:
                    response = {
                        "fulfillmentText": fulfillment_text['fulfillment_text'],
                        "fulfillmentMessages": fulfillment_messages['fulfillment_messages'],
                        "followupEventInput": followup_event_input['followup_event_input']
                    }
                else:
                    response = {
                        "fulfillmentText": fulfillment_text['fulfillment_text'],
                        "followupEventInput": followup_event_input['followup_event_input']
                    }
        else:
            if output_contexts is not None:
                if fulfillment_messages is not None:
                    response = {
                        "fulfillmentText": fulfillment_text['fulfillment_text'],
                        "fulfillmentMessages": fulfillment_messages['fulfillment_messages'],
                        "outputContexts": output_contexts['output_contexts']
                    }
                else:
                    response = {
                        "fulfillmentText": fulfillment_text['fulfillment_text'],
                        "outputContexts": output_contexts['output_contexts']
                    }
            else:
                if fulfillment_messages is not None:
                    response = {
                        "fulfillmentText": fulfillment_text['fulfillment_text'],
                        "fulfillmentMessages": fulfillment_messages['fulfillment_messages']
                    }
                else:
                    response = {
                        "fulfillmentText": fulfillment_text['fulfillment_text']
                    }

        # return the main dialogflow response
        return response


class UserModel:
    def __init__(self):
        self.user_id = ""
        self.last_update = ""
        self.current_food_category = ""


# run Flask app
if __name__ == "__main__":
    app.run()
