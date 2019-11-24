from flask import Flask, request, jsonify, render_template
import os
import dialogflow
import requests
import json
import pusher
import time

app = Flask(__name__)

user_info_dic = {}

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
    # fulfillmentText = 'Basic card Response from webhook'
    # aog = actions_on_google_response()
    # aog_sr = aog.simple_response([
    #     [fulfillmentText, fulfillmentText, False]
    # ])
    #
    # basic_card = aog.basic_card("Title", "Subtitle", "This is formatted text",
    #                             image=["https://www.pragnakalp.com/wp-content/uploads/2018/12/logo-1024.png",
    #                                    "this is accessibility text"])
    #
    # ff_response = fulfillment_response()
    # ff_text = ff_response.fulfillment_text(fulfillmentText)
    #
    # fb = facebook_response()
    # texts = ['text1']
    # text_res = fb.text_response(texts)
    #
    # ff_messages = ff_response.fulfillment_messages([text_res])
    # print("===ready to replay==")
    # reply = ff_response.main_response(ff_text, ff_messages)
    # return reply
    # ---------------------------
    # intent_name = data['queryResult']['intent']['displayName']
    # response = "nothing"
    # if intent_name == INTENT_MOVIE:
    #     response = "movie"
    # elif intent_name == INTENT_FOOD_CATEGORY:
    #     response = "food category"
    # return response
    # -------------------
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
            # # text response
            # title = ['Please choose a Category:']
            # text_res = fb_platform.text_response(title)
            # # card response
            # card_response = fb_platform.card_advance_response()
            #
            # # facebook_messages = ff_response.fulfillment_messages([card_response])

            title = ['Please choose a Category:']
            text_res = fb_platform.text_response(title)

            buttons = [
                ['button1', 'hello'],
                ['button2', 'hello again']
            ]

            card1 = fb_platform.make_card_response("title1", "subtitle1",
                                                   "http://jalilurrahman.com/ChatBotImageResource/cover.jpeg", buttons)
            card2 = fb_platform.make_card_response("title2", "subtitle2",
                                                   "http://jalilurrahman.com/ChatBotImageResource/cover.jpeg", buttons)
            card3 = fb_platform.make_card_response("title3", "subtitle3",
                                                   "http://jalilurrahman.com/ChatBotImageResource/cover.jpeg", buttons)
            card_response = fb_platform.card_full_fillment(title, [card1, card2, card3])

            reply = ff_response.main_response(fulfillment_message, card_response)
            print(reply)
            return reply
        elif food_type == "Mexicun":
            print("not found")
            pass
    return food_type


# Helper method
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
