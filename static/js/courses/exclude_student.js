console.log("Load exclude student js")

const modalBtns = [...document.getElementsByClassName("modal-button")]
const modalBody = document.getElementById("modal-body-confirm")
const excludeBtn = document.getElementById("exclude-button")
const csrf = document.getElementsByName("csrfmiddlewaretoken")
const url = window.location.href

modalBtns.forEach(modalBtn=> modalBtn.addEventListener("click", ()=>{
    const student_pk = modalBtn.getAttribute("data-student-pk")
    const course_pk = modalBtn.getAttribute("data-course-pk")
    const studentName = modalBtn.getAttribute("data-student-name")
    const courseTitle = modalBtn.getAttribute("data-course-title")

    const studentBlock = document.getElementById(`student-block-${student_pk}`)

    modalBody.innerHTML = `
        <div class="h6 mb-3">Вы уверены, что хотите исключить студента "<b>${studentName}</b>" из курса "<b>${courseTitle}</b>"?<div>
    `

    excludeBtn.addEventListener("click", ()=>{

        $.ajax({
            type: "POST",
            url: url + `/exclude/` + student_pk,
            data: {"csrfmiddlewaretoken": csrf[0].value, "course_pk": course_pk, "student_pk": student_pk},
            success: function(response){
                console.log("Student excluded successfully")
                studentBlock.remove()
                $("#excludeStudentModal").modal("hide")
            },
            error: function(error){
                console.log(error)
            }
        })
    })
}))
