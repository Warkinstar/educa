console.log("hello world quiz")
const url = window.location.href

const quizBox = document.getElementById("quiz-box")
let data
// Делает запрос к представлению quiz_data_view, для получения вопросов с соответствующими ответами
$.ajax({
    type: "GET",
    url: `${url}data`,
    success: function(response){
        // console.log(response)
        const data = response.data
        data.forEach(el => {
            for (const [question, answers] of Object.entries(el)){
                quizBox.innerHTML += `
                    <hr>
                    <div class="mb-2">
                        <b>${question}</b>
                    </div>
                `
                answers.forEach(answer=> {
                    quizBox.innerHTML += `
                        <div>
                            <input type="radio" class="ans" id="${question}-${answer}" name="${question}" value="${answer}">
                            <label for="${question}">${answer}</label>
                        </div>
                    `
                })
            }
        });

    },
    error: function(error){
        console.log(error)
    }
})

const quizForm = document.getElementById("quiz-form")
const csrf = document.getElementsByName("csrfmiddlewaretoken")

// Выполняется в момент, когда пользователь нажимает на кнопку закончить тест
const sendData = () => {
    const elements = [...document.getElementsByClassName("ans")]  // Собираем все варианты ответов в массив
    const data = {}
    data["csrfmiddlewaretoken"] = csrf[0].value  // добавляем csrf в словарь data
    elements.forEach(el=>{  // перебираем варианты ответов
        if (el.checked) {  // если вариант отмечен
            data[el.name] = el.value  // добавляем отмеченный вариант в словарь в виде question: answer
        } else {
            if (!data[el.name]) {  // Если вариант не отмечен и его еще нет в словаре
                data[el.name] = null  // question: []
            }
        }
    })
    // Запрос в представление save_quize_view, передает данные теста с ответами пользователя
    $.ajax({
        type: "POST",
        url: `${url}save`,
        data: data,
        success: function(response){
            console.log(response)
        },
        error: function(error){
            console.log(error)
        }
    })
}

quizForm.addEventListener("submit", e=>{
    e.preventDefault()

    sendData()
})
