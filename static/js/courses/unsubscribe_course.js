// Делает ajax запрос на исключения request.user из courses.students

console.log("unsubscribe script loaded successfully")

const modalBtns = [...document.getElementsByClassName("modal-button")]
const modalBody = document.getElementById("modal-body-confirm")
const unsubscribeBtn = document.getElementById("unsubscribe-course-button")
const csrf = document.getElementsByName("csrfmiddlewaretoken")
const url = window.location.href

modalBtns.forEach(modalBtn=> modalBtn.addEventListener("click", ()=>{
    const course_pk = modalBtn.getAttribute("data-course-pk")
    const course_title = modalBtn.getAttribute("data-course-title")

    const course_block = document.getElementById(`course-block-${course_pk}`)

    modalBody.innerHTML = `
        <div class="h6">Вы уверены что хотите отписаться от курса "${course_title}"?</div>
    `

    unsubscribeBtn.addEventListener("click", ()=>{
        $.ajax({
            type: "POST",
            url: url + `${course_pk}/unsubscribe/`,
            data: {"csrfmiddlewaretoken": csrf[0].value, "course_pk": course_pk},
            success: function(response){
                console.log(`Unsubscribed from the course ${course_title} was successfully`)
                course_block.remove()
                $("#unsubscribeCourseModal").modal("hide")
            },
            error: function(error){
                console.log(error)
            }
        })
    })
}))

