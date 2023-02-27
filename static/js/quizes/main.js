console.log("hello world!");

const modalBtns = [...document.getElementsByClassName("modal-button")]
const modalBody = document.getElementById("modal-body-confirm")
const startBtn = document.getElementById("start-button")

const url = window.location.href

modalBtns.forEach(modalBtn=> modalBtn.addEventListener("click", ()=>{
    const pk = modalBtn.getAttribute("data-pk")
    const name = modalBtn.getAttribute("data-quiz")
    const numQuestions = modalBtn.getAttribute("data-questions")
    const difficulty = modalBtn.getAttribute("data-difficulty")
    const scoreToPass = modalBtn.getAttribute("data-pass")
    const time = modalBtn.getAttribute("data-time")

    modalBody.innerHTML = `
        <div class="h5 mb-3">Вы уверены что хотите начать тест "<b>${name}</b>"?</div>
        <div class='text-muted'>
            <ul>
                <li>Сложность: <b>${difficulty}</b></li>
                <li>Количество вопросов: <b>${numQuestions}</b></li>
                <li>Проходной процент: <b>${scoreToPass} %</b></li>
                <li>Время на тест: <b>${time} мин.</b></li>
            </ul>
        </div>
    `

    startBtn.addEventListener("click", ()=>{
        window.location.href = url + pk
    })
}))