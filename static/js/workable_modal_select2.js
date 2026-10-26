(function () {
    var oldSelect2 = jQuery.fn.select2;
    jQuery.fn.select2 = function () {
        const modalParent = jQuery(this).parents('div.modal').first();
        if (arguments.length === 0 && modalParent.length > 0) {
            arguments = [{dropdownParent: modalParent}];
        } else if (arguments.length === 1
            && typeof arguments[0] === 'object'
            && typeof arguments[0].dropdownParent === 'undefined'
            && modalParent.length > 0) {
            arguments[0].dropdownParent = modalParent;
        }
        return oldSelect2.apply(this, arguments);
    };
    for (var key in oldSelect2) {
        jQuery.fn.select2[key] = oldSelect2[key];
    }
})();