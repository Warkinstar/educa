// Делает ajax запрос на исключение request.user из courses.students и деактивацию личного назначения

console.log("unsubscribe script loaded successfully");

const modalBtns = [...document.getElementsByClassName("modal-button")];
const modalBody = document.getElementById("modal-body-confirm");
const unsubscribeBtn = document.getElementById("unsubscribe-course-button");
const csrf = document.getElementsByName("csrfmiddlewaretoken");
const modalEl = document.getElementById("unsubscribeCourseModal");

let selectedCoursePk = null;
let selectedCourseTitle = null;
let selectedUnsubscribeUrl = null;

modalBtns.forEach((modalBtn) => {
    modalBtn.addEventListener("click", () => {
        selectedCoursePk = modalBtn.getAttribute("data-course-pk");
        selectedCourseTitle = modalBtn.getAttribute("data-course-title");
        selectedUnsubscribeUrl =
            modalBtn.getAttribute("data-unsubscribe-url") ||
            `${window.location.pathname.replace(/\/?$/, "/")}${selectedCoursePk}/unsubscribe/`;

        if (modalBody) {
            modalBody.innerHTML = `
                <div class="h6">Вы уверены, что хотите отписаться от курса «${selectedCourseTitle}»?</div>
            `;
        }
    });
});

if (unsubscribeBtn) {
    unsubscribeBtn.addEventListener("click", () => {
        if (!selectedCoursePk || !selectedUnsubscribeUrl) return;

        const courseBlock = document.getElementById(`course-block-${selectedCoursePk}`);

        $.ajax({
            type: "POST",
            url: selectedUnsubscribeUrl,
            data: {
                csrfmiddlewaretoken: csrf.length ? csrf[0].value : "",
                course_pk: selectedCoursePk,
            },
            success: function () {
                console.log(`Unsubscribed from the course ${selectedCourseTitle} successfully`);
                if (courseBlock) {
                    courseBlock.remove();
                }
                if (window.bootstrap && modalEl) {
                    const modalInstance = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
                    modalInstance.hide();
                } else {
                    $("#unsubscribeCourseModal").modal("hide");
                }
            },
            error: function (error) {
                console.error(error);
            },
        });
    });
}


