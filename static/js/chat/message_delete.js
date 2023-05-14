console.log("Message delete script loaded");

const modalBtns = [...document.getElementsByClassName("modal-button")]
const modalBody = document.getElementById("modal-body-confirm")
const deleteBtn = document.getElementById("delete-content-button")
const csrf = document.getElementsByName("csrfmiddlewaretoken")
const url = window.location.href

modalBtns.forEach(modalBtn=> modalBtn.addEventListener("click", ()=>{
    const message_pk = modalBtn.getAttribute("data-message-pk")
    const message_content = modalBtn.getAttribute("data-message-content")
    const message_time = modalBtn.getAttribute("data-message-time")
    const user_full_name = modalBtn.getAttribute("data-message-user-full-name")

    const message_block = document.getElementById(`message-block-${message_pk}`)

    modalBody.innerHTML = `
        <div class="h6 mb-3">Вы уверены что хотите удалить сообщение "${message_content}"
        пользователя "<b>${user_full_name}</b>" ${message_time}</div>
    `

    deleteBtn.addEventListener("click", ()=>{
        $.ajax({
            type: "POST",
            url: url + `message/${message_pk}/` + `delete`,
            data: {"csrfmiddlewaretoken": csrf[0].value, "message_pk": message_pk},
            success: function(response){
                console.log(`Message ${message_content} deleted successfully`)
                message_block.remove()
                $("#messageDeleteModal").modal("hide")
            },
            error: function(error){
                console.log(error)
            }
        })
    })
}))