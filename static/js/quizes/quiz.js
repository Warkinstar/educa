console.log("hello world quiz")
const url = window.location.href

// Атрибуты шаблона, для дальнешего использования
const quizBox = document.getElementById("quiz-box")
const scoreBox = document.getElementById("score-box")
const resultBox = document.getElementById("result-box")

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
            // Обработка ответа представления
            // console.log(response)
            const results = response.results  // Берем результаты с ответа
            console.log(results)
            quizForm.classList.add("not-visible")  // Скрыть тест

            // Условие если пользователь прошел тест или нет. Вывести результат.
            scoreBox.innerHTML += `${response.passed ? 'Поздравляем вы прошли тест! ' : 'Вы не прошли тест... '}Ваш результат: ${response.score.toFixed(2)}% `

            results.forEach(res=>{
                const resDiv = document.createElement("div")
                for (const [question, resp] of Object.entries(res)){
                    /*console.log(question)
                    console.log(resp)
                    console.log("****")*/

                    // Отобразить вопрос
                    resDiv.innerHTML += question
                    const cls = ["container", "p-3", "text-light", "h6"]
                    resDiv.classList.add(...cls)

                    if (resp=="не отмечен") {
                        resDiv.innerHTML += "- не отмечен"
                        resDiv.classList.add("bg-danger")
                    }
                    else {
                        const answer = resp["answered"]
                        const correct = resp["correct_answer"]
                        console.log(answer, correct)

                        if (answer == correct) {
                            resDiv.classList.add("bg-success")
                            // Здесь можно добавить сам вопрос
                            resDiv.innerHTML += ` вы ответили: ${answer}`
                        } else {
                            resDiv.classList.add("bg-danger")
                            // Здесь можно добавить сам вопрос
                            resDiv.innerHTML += ` | правильный вариант: ${correct}`
                            resDiv.innerHTML += ` | вы ответили: ${answer}`
                        }
                    }
                }
                // Добавить в тело
                // const body = document.getElementsByTagName("BODY")[0]
                resultBox.append(resDiv)
            })
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
