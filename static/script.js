function confirmDelete(message) {
    return confirm(message);
}

setTimeout(function () {
    const flashMessages = document.querySelectorAll(".flash");

    flashMessages.forEach(function (message) {
        message.style.display = "none";
    });
}, 3500);