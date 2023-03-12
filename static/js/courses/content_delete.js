console.log("Content delete loaded")

const modalBtns = [...document.getElementsByClassName("modal-button")]
const modalBody = document.getElementById("modal-body-confirm")
const deleteBtn = document.getElementById("delete-content-button")
const csrf = document.getElementsByName("csrfmiddlewaretoken")
const url = window.location.href

modalBtns.forEach(modalBtn=> modalBtn.addEventListener("click", ()=>{
    const content_pk = modalBtn.getAttribute("data-content-pk")
    const content_item_name = modalBtn.getAttribute("data-content-item-name")

    const contentBlock = document.getElementById(`content-block-${content_pk}`)

    modalBody.innerHTML = `
        <div class="h6 mb-3">Вы уверены, что хотите удалить контент "<b>${content_item_name}"?</div>
    `

    deleteBtn.addEventListener("click", ()=>{

        $.ajax({
            type: "POST",
            url: url + `content/${content_pk}/` + `delete`,
            data: {"csrfmiddlewaretoken": csrf[0].value, "content_pk": content_pk},
            success: function(response){
                console.log(`Content ${content_item_name} deleted successfully`)
                contentBlock.remove()
                $("#contentDeleteModal").modal("hide")
            },
            error: function(error){
                console.log(error)
            }
        })
    })
}))