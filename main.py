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
USE_ADMIN = True
ADMIN_NAME = "Admin"
ADMIN_TOKEN = "admin"

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

@server.route("/admin", methods=["GET"])
def admin():
    return flask.render_template("admin.html")

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

    nickname = sanitise(data.get("nickname")).strip().replace(" ", "")
    if nickname in [None, ""] or len(nickname) > MAX_NICKNAME_LEN:
        return ERROR_MALFORMED

    if nickname.lower() == ADMIN_NAME:
        return ("Cannot use admin name.", 401)

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

    # allow admins to inject raw html cus funny
    content = sanitise(data.get("content")).strip() if users[user_index][1] != ADMIN_TOKEN else data.get("content").strip()
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

@server.route("/api/admin", methods=["POST"])
def api_admin():
    user_index = find_index(users, 1, parse_auth())
    method = flask.request.method
    data = flask.request.json

    if not USE_ADMIN:
        return ("Admin is disabled on this server.", 401)

    if user_index == -1:
        return ERROR_UNAUTHORISED

    if users[user_index][1] != ADMIN_TOKEN:
        return ERROR_UNAUTHORISED

    command = data.get("command")
    if command in ["", None]:
        return ("Invalid command.", 400)

    parts = command.split(" ")
    command = parts[0]

    if command == "ban":
        user = find_index(users, 0, parts[1])
        if user == -1:
            return ("Could not find user.", 404)
        if user == user_index:
            return ("Cannot ban self.", 400)
        users[user][0] = f"{users[user][0]} <b style=\"color:lightcoral\">(Banned)</b>"
        users[user][1] = generate_key()
        return SUCCESS_DONE
    elif command == "clear":
        messages.clear()
        return ("Cleared messages.", 200)
    elif command == "send":
        username = parts[1]
        user = find_index(users, 0, username)
        if user == -1:
            return ("User not found.", 404)
        content = parts[2:]
        add_message(user, " ".join(content))
        return ("Created message.", 201)

    else:
        return ("Invalid command.", 400)


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
        # add admin account if not one already
        if USE_ADMIN and find_index(users, 1, ADMIN_TOKEN) == -1:
            add_user(ADMIN_NAME)
            users[-1][1] = ADMIN_TOKEN
        server.run(*HOST_ADDRESS)
    except KeyboardInterrupt:
        pass
    finally:
        if not AMNESIA:
            json.dump({ "messages": messages, "users": users, "blocks": blocks },
                      open(STORAGE, "w"), indent=4)
            print("Saved data.")

