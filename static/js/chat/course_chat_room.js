document.addEventListener('DOMContentLoaded', function() {
  console.log("course_chat_room script successfully included");
});

const courseId = JSON.parse(document.getElementById("course-id").textContent);  // course.id from json format
const requestUser = JSON.parse(document.getElementById("request-user").textContent); // requesUser from json format
const input = document.getElementById("chat-message-input");  // message input
const submitButton = document.getElementById("chat-message-submit");  // message button
const chat = document.getElementById("chat");  // chat id
chat.scrollTop = chat.scrollHeight;  // scroll down chat window


// focus input area
input.focus();

// Прослушка клавиши enter для отправки сообщения
input.addEventListener("keypress", function(event) {
    if (event.keyCode === 13) {  // ==="enter"
      // cancel the default action, if needed
      event.preventDefault();
      // trigger click event on button
      submitButton.click();
    }
});

// Определение прослушки событий нажатия на кнопку отправки сообщения
submitButton.addEventListener("click", function(event) {
    const message = input.value;  // Извлекаем значение сообщения
    if (message) {  // Если сообщение не пустое
      // send message in JSON format on websocket
      chatSocket.send(JSON.stringify({"message": message}));
      // clear input
      input.value = '';
      input.focus();
    }
});

let chatSocket = null;

function connect(){
    // Подключаем webSocket к страничке wss:// for prod; ws:// for local #}  // window.location.host - адрес-хост сайта
    const url = "ws://" + window.location.host + "/ws/chat/room/" + courseId + "/";
    chatSocket = new WebSocket(url);

    chatSocket.onopen = function(e) {
        console.log("Successfully connected to the WebSocket.");
    }

    chatSocket.onclose = function(event) {
        console.error("WebSocket connection closed unexpectedly. Trying to reconnect in 2s...");
        setTimeout(function(e) {
            console.log("Reconnecting...");
            connect();
        }, 2000);
    };

    // Эта функция срабатывает когда получаем данные (сообщения) через ВебСокет
    chatSocket.onmessage = function (event) {
        const data = JSON.parse(event.data);

        const dateOptions = {hour: 'numeric', minute: 'numeric', hour12: true};
        const datetime = new Date(data.datetime).toLocaleString(dateOptions);  <!-- ('en', dateOptions)  -->
        const isMe = data.user === requestUser;
        const source = isMe ? "me" : "other";
        const name = isMe ? "Me" : data.user_full_name;

        // Добавить сообщение в чат и заскроллить вниз
        if (isMe) {
          chat.innerHTML += '<div class="d-flex justify-content-end"><div class="alert alert-success" role="alert"><div class="fst-italic fw-bold">' + datetime + '</div>' + data.message + '</div></div>';
        } else {
          chat.innerHTML += '<div class="d-flex justify-content-start"><div class="alert alert-primary" role="alert"><div class="fst-italic fw-bold">' + datetime + '</div><b>' + data.user_full_name + '</b>: ' + data.message + '</div></div>';
        }
        chat.scrollTop = chat.scrollHeight - chat.clientHeight; // Прокрутить чат вниз

    };

    chatSocket.onerror = function(err) {
        console.log("WebSocket encountered an error: " + err.message);
        console.log("Closing the socket.");
        chatSocket.close();
    }
}

connect();



