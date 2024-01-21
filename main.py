# Include required libraries
import io, html.parser
import random, string
import flask, json


# Configuration
HOST_ADDRESS = ( "0.0.0.0", 5500 )
MAX_NICKNAME_LEN = 12
KEY_LENGTH = 16
STORAGE = "storage.json"
AMNESIA = False


# Generic codes and their messages
ERROR_MALFORMED = ("400: Malformed request data.", 400)
ERROR_UNAUTHORISED = ("401: No authentication key.", 401)
ERROR_NOT_FOUND = ("404: Not found.", 404)
SUCCESS_DONE = ("200: Done.", 200)
SUCCESS_CREATED = ("201: Created.", 201)
SUCCESS_CHANGED = ("201: Changed.", 201)

server = flask.Flask(__name__)

users = [] # [ ["nickname", "key"] ]
messages = [] # [ (user_index, "content") ]
blocks = [] # [ (user_index, user_index) ]

generate_key = lambda : "".join([random.choice(string.ascii_lowercase + string.punctuation) for x in range(KEY_LENGTH)])
add_user = lambda nickname : users.append([nickname, generate_key()])
add_message = lambda user_index, content : messages.append((user_index, content))
add_block = lambda user1_index, user2_index : blocks.append(user1_index, user2_index)
parse_auth = lambda : str(flask.request.authorization).strip().lower()

def find_index(l: list, i: int, v: object) -> int:
    for x in range(len(l)):
        if l[x][i] == v:
            return x
    return -1


class Sanitiser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs= True
        self.text = io.StringIO()
    def handle_data(self, d):
        self.text.write(d)
    def get_data(self):
        return self.text.getvalue()

def sanitise(v: str) -> str:
    s = Sanitiser()
    s.feed(v)
    return s.get_data()


@server.route("/", methods=["GET"])
def index():
    return flask.render_template("index.html")

@server.route("/account", methods=["GET"])
def account():
    return flask.render_template("account.html")

@server.route("/chat", methods=["GET"])
def chat():
    return flask.render_template("chat.html")

@server.route("/users", methods=["GET"])
def users():
    return flask.render_template("users.html")

@server.route("/api/auth", methods=["GET"])
def api_auth():
    user_index = find_index(users, 1, parse_auth())
    
    return ERROR_UNAUTHORISED if user_index == -1 else (users[user_index][0], 200)

@server.route("/api/users", methods=["GET", "POST", "PATCH"])
def api_users():
    user_index = find_index(users, 1, parse_auth())
    method = flask.request.method

    if method == "GET":
        return flask.jsonify([u[0] for u in users])
    
    data = flask.request.json

    nickname = data.get("nickname")
    if nickname in [None, ""] or len(nickname) > MAX_NICKNAME_LEN:
        return ERROR_MALFORMED

    if find_index(users, 0, nickname) != -1 and users[user_index][0] != nickname:
        return ("Nickname taken.", 401)

    if method == "POST":
        add_user(nickname)
        return (users[-1][1], 201)

    if user_index == -1:
        return ERROR_UNAUTHORISED

    users[user_index][0] = nickname
    return SUCCESS_CHANGED

@server.route("/api/messages", methods=["GET", "POST"])
def api_messages():
    user_index = find_index(users, 1, parse_auth())
    method = flask.request.method
    
    if method == "GET":
        return flask.jsonify([[users[m[0]][0], m[1]] for m in messages])

    data = flask.request.json

    if user_index == -1:
        return ERROR_UNAUTHORISED

    content = sanitise(data.get("content")).strip()
    if content in [None, ""]:
        return ERROR_MALFORMED
    
    add_message(user_index, content)
    return SUCCESS_CREATED

@server.route("/api/blocks", methods=["GET", "POST", "DELETE"])
def api_blocks():
    user_index = find_index(users, 1, parse_auth())
    method = flask.request.method

    if user_index == -1:
        return ERROR_UNAUTHORISED

    if method == "GET":
        blks = []
        for u1, u2 in blocks:
            if u1 == user_index:
                blks.append(u2)
        return flask.jsonify(blks)
    
    data = flask.request.json

    try:
        identifier = int(data.get("identifier", -1))
    except:
        identifier = -1
    finally:
        if identifier in [None, ""] or identifier < 0 or identifier > len(users)-1:
            return ERROR_MALFORMED

    block = [user_index, identifier]
    if method == "POST":
        if user_index == identifier:
            return ("Cannot block yourself.", 400)
        if block in blocks:
            return SUCCESS_DONE
        blocks.append(block)
        return SUCCESS_CREATED

    if not block in blocks:
        return ERROR_MALFORMED
    blocks.remove(block)
    return SUCCESS_DONE

if __name__ == "__main__":
    if not AMNESIA:
        storage = {}
        try:
            storage = json.load(open(STORAGE, "r"))
        except:
            pass
        messages = storage.get("messages", [])
        users = storage.get("users", [])
        blocks = storage.get("blocks", [])
    try:
        server.run(*HOST_ADDRESS)
    except KeyboardInterrupt:
        pass
    finally:
        if not AMNESIA:
            json.dump({ "messages": messages, "users": users, "blocks": blocks },
                      open(STORAGE, "w"), indent=4)
            print("Saved data.")

