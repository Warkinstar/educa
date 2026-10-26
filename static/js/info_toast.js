function createToastElement(message, bgClass, iconClass) {
    let container = document.getElementById('toastContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        container.style.zIndex = '1050';
        document.body.appendChild(container);
    }
    const toastEl = document.createElement('div');
    toastEl.className = 'toast align-items-center text-bg-' + bgClass + ' border-0';
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.setAttribute('aria-atomic', 'true');
    toastEl.setAttribute('data-bs-autohide', 'true');

    const dFlex = document.createElement('div');
    dFlex.className = 'd-flex';

    const body = document.createElement('div');
    body.className = 'toast-body d-flex align-items-center';

    const icon = document.createElement('i');
    icon.className = iconClass + ' me-2 flex-shrink-0';
    body.appendChild(icon);

    const textSpan = document.createElement('span');
    textSpan.textContent = message; // Защита от XSS
    body.appendChild(textSpan);

    const closeBtn = document.createElement('button');
    closeBtn.type = 'button';
    closeBtn.className = 'btn-close btn-close-white me-2 m-auto';
    closeBtn.setAttribute('data-bs-dismiss', 'toast');
    closeBtn.setAttribute('aria-label', 'Close');

    dFlex.appendChild(body);
    dFlex.appendChild(closeBtn);
    toastEl.appendChild(dFlex);

    container.appendChild(toastEl);
    return toastEl;
}

function showErrorToast(message) {
    const toastEl = createToastElement(message, 'danger', 'bi bi-exclamation-triangle-fill');
    const bsToast = new bootstrap.Toast(toastEl, { delay: 6000 });
    bsToast.show();
    toastEl.addEventListener('hidden.bs.toast', () => { toastEl.remove(); });
}

function showInfoToast(message) {
    const toastEl = createToastElement(message, 'info', 'bi bi-info-circle-fill');
    const bsToast = new bootstrap.Toast(toastEl, { delay: 4000 });
    bsToast.show();
    toastEl.addEventListener('hidden.bs.toast', () => { toastEl.remove(); });
}
