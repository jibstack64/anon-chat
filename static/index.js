
/* Configuration */

const REFRESH = 5000

const getToken = () => localStorage.getItem("token")
const setToken = (v) => localStorage.setItem("token", v)
var globalUsers = []
var globalMessages = []
var globalBlocks = []

/* JS utilities */

function redirect(path) {
    window.location.replace(`/${path}`)
}

/* HTTP utilities */

// Makes a request to `ADDRESS/path` and returns the result.
function makeRequest(method, path, data, auth, func) {

    // I mean... it works
    const http = new XMLHttpRequest();
    http.open(method, `/${path}`)
    if (auth != null) {
        http.setRequestHeader("Authorization", auth)
    }
    if (method != "GET") {
        http.setRequestHeader("Content-Type", "application/json")
    }
    if (data != null) {
        data = JSON.stringify(data)
    }
    http.send(data)

    http.onreadystatechange = () => {
        // Check for unmanageable errors before running the handler function
        let code = http.status, data = http.responseText
        
        switch (code) {
            case 404:
            case 400:
                return allAlert(data)
            default:
                func(code, data)
        }

    }

}

/* API interfacing */

const apiUsers = (method, nickname, handler) =>
    makeRequest(method, "api/users", { "nickname": nickname }, getToken(), handler)
const apiMessages = (method, content, handler) =>
    makeRequest(method, "api/messages", { "content": content }, getToken(), handler)
const apiAuth = (token, handler) =>
    makeRequest("GET", "api/auth", null, token, handler)
const apiBlocks = (method, identifier, handler) =>
    makeRequest(method, "api/blocks", { "identifier": identifier }, getToken(), handler)

/* --> *.html */

function allAlert(text) {
    let topBar = document.getElementById("topbar")
    topBar.innerHTML = text
    setTimeout(() => { topBar.innerHTML = "" }, 2500)
}

// FILL 'EM!
apiUsers("GET", null, (_, data) => {
    try {
        globalUsers = JSON.parse(data)
    } catch {
        return
    }
})
apiMessages("GET", null, (_, data) => {
    try {
        globalMessages = JSON.parse(data)
    } catch {
        return
    }
})
apiBlocks("GET", null, (_, data) => {
    try {
        globalBlocks = JSON.parse(data)
    } catch {
        return
    }
})

/* --> chat.html */

function chatInit() {
    // Check that the stored token is (still?) valid
    apiAuth(getToken(), (code, _) => {
        if (code != 200) {
            redirect("account")
        }
    })

    // "Enter" OR button works!
    let messageBox = document.getElementById("chat-messages")
    messageBox.addEventListener("keypress", (event) => {
        if (event.key == "Enter") {
            chatSend()
        }
    })
    messageBox.onclick = chatSend

    // Begin updating the chat
    chatUpdate()
    setInterval(chatUpdate, REFRESH)
}

/* Update the chat list with the new messages. */
function chatUpdate() {
    let messageList = document.getElementById("chat-messages")
    apiMessages("GET", null, (_, data) => {
        try {
            globalMessages = JSON.parse(data)
        } catch {
            return
        }
        messageList.innerHTML = ""
        for (const content of [...globalMessages].reverse()) {
            messageList.innerHTML += `
            <div class="message">
                <div class="message-user">
                    ${content[0]}
                </div>
                <div class="message-content">
                    ${!(globalBlocks.includes(globalUsers.indexOf(content[0]))) ? content[1] :
                    "<b style='color: lightcoral'>BLOCKED</b>"}
                </div>
            </div>
            `
        }
    })
}

function chatSend() {
    let messageBox = document.getElementById("message-box")
    apiMessages("POST", messageBox.value, (_, __) => {
        messageBox.value = ""
        chatUpdate()
    })
}

/* --> account.html */

function accountInit() {
    let nicknameBox = document.getElementById("nickname")
    let tokenBox = document.getElementById("password")
    apiAuth(getToken(), (code, data) => {
        if (code == 200) {
            nicknameBox.value = data
            tokenBox.value = getToken()
        } else {
            nicknameBox.value = ""
            tokenBox.value = ""
            setToken("")
            allAlert("Type your nickname and click submit to sign up.")
        }
    })
    accountUpdate() // All we need to do :p
}

function accountUpdate() {
    // Fill input fields
    let nicknameBox = document.getElementById("nickname")
    let tokenBox = document.getElementById("password")
    apiAuth(getToken(), (code, data) => {
        if (code == 200) {
            nicknameBox.value = data
            tokenBox.value = getToken()
        } else {
            nicknameBox.value = ""
            tokenBox.value = ""
            allAlert("Type your nickname and click submit to sign up.")
        }
    })
}

function accountSubmit() {
    // Create new account if one is not there already
    let nicknameBox = document.getElementById("nickname")
    if (getToken() == null || getToken() == "") {
        apiUsers("POST", nicknameBox.value, (code, data) => {
            if (code != 201) { return allAlert(data) }
            setToken(data)
            allAlert("Created account. You can now access the chat.")
            accountUpdate()
        })
    } else {
        apiUsers("PATCH", nicknameBox.value, (code, data) => {
            if (code != 201) { return allAlert(data) }
            allAlert("Updated nickname.")
            accountUpdate()
        })
    }
}

/* --> users.html */

function usersInit() {
    usersUpdate()
    setInterval(usersUpdate, REFRESH)
}

function usersUpdate() {
    let userList = document.getElementById("user-list")
    apiBlocks("GET", null, (_, blockList) => {
        try {
            globalBlocks = JSON.parse(blockList)
        } catch {
            return
        }
        apiUsers("GET", null, (_, data) => {
            try {
                globalUsers = JSON.parse(data)
            } catch {
                return
            }
            userList.innerHTML = ""
            for (let i = 0; i < globalUsers.length; i++) {
                userList.innerHTML += `
                <li class="user">
                    ${globalUsers[i]}
                    <button onclick="usersBlock(${i})">
                        ${(globalBlocks.includes(i) ? "Unblock" : "Block")}
                    </button>
                </li>
                `
            }
        })
    })
}

function usersBlock(id) {
    if (!globalBlocks.includes(id)) {
        apiBlocks("POST", id, (_, __) => {
            allAlert(`Blocked ${globalUsers[id]}.`)
            usersUpdate()
        })
    } else {
        apiBlocks("DELETE", id, (_, __) => {
            allAlert(`Unblocked ${globalUsers[id]}.`)
            usersUpdate()
        })
    }
}
