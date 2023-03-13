console.log("Load question delete js")

const modalBtns = [...document.getElementsByClassName("modal-button")]  // Масив кнопок
const modalBody = document.getElementById("modal-body-confirm")  //  body modal
const deleteBtn = document.getElementById("delete-button")  // кнопка в modal

// const url = window.location.href

// Наполнить modal информацией с подтверждением удаления вопроса
modalBtns.forEach(modalBtn=> modalBtn.addEventListener("click", ()=>{
    const pk = modalBtn.getAttribute("data-question-pk")
    const name = modalBtn.getAttribute("data-question-text")
    const created = modalBtn.getAttribute("data-question-created")

    modalBody.innerHTML = `
        <div class="ht mb-3">Вы уверены что хотите удалить вопрос "<b>${name}</b>"?</div>
        <b>Вопрос был создан: </b>${created}
    `
    // установить pk в data атрибут deleteBtn
    deleteBtn.setAttribute("data-question-pk", pk)
    deleteBtn.setAttribute("data-question-url-delete", modalBtn.getAttribute("data-question-url-delete"))
}))

// Выловить csrf токен
const csrf = document.getElementsByName("csrfmiddlewaretoken")

// Если была нажата кнопка удалить
deleteQuestion = () =>{
    const pk = deleteBtn.getAttribute("data-question-pk") // получить pk из data атрибута deleteBtn
    const url_delete = deleteBtn.getAttribute("data-question-url-delete")  // Получить url для удаления
    const question = document.getElementById(`question-${pk}`)  // Найти удаляемый вопрос на странице

    // Отправить запрос на удаление
    $.ajax({
        type: "POST",
        url: `${url_delete}`,
        data: {"pk": pk, "csrfmiddlewaretoken": csrf[0].value},
        success: function(response){

            question.remove()  // Удалить вопрос из шаблона
            console.log("Question removed successfully")
            $('#questionDeleteModal').modal('hide')  // Закрыть modal
        },
        error: function(error){
            console.log(error)
        }
    })
}

deleteBtn.addEventListener("click", ()=>{

    deleteQuestion()

})