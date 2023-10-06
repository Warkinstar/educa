// custom javascript
const url = window.location.href

$(document).ready(() => {
  console.log('Sanity Check!');
});

$('.button').on('click', function() {
  $.ajax({
    url: `/pages/main/tasks/`,
    data: { type: $(this).data('type') },
    method: 'POST',
  })
  .done((res) => {
    getStatus(res.task_id);
  })
  .fail((err) => {
    console.log(err);
  });
});

function getStatus(taskID) {
  $.ajax({
    url: `/pages/main/tasks/${taskID}/`,
    method: 'GET'
  })
  .done((res) => {
    const html = `
      <tr class="${getStatusClass(res.task_status)}">
        <td>${res.task_id}</td>
        <td>${res.task_status}</td>
        <td>${res.task_result}</td>
      </tr>`
    $('#tasks').prepend(html);

    const taskStatus = res.task_status;

    if (taskStatus === 'SUCCESS' || taskStatus === 'FAILURE') return false;
    setTimeout(function() {
      getStatus(res.task_id);
    }, 1000);
  })
  .fail((err) => {
    console.log(err)
  });
}

function getStatusClass(taskStatus) {
  switch (taskStatus) {
    case 'SUCCESS':
      return 'table-success';
    case 'FAILURE':
      return 'table-danger';
    case 'PENDING':
      return 'table-warning';
    default:
      return '';
  }
}