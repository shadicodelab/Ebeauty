document.addEventListener("DOMContentLoaded", function () {
    const nav = document.querySelector("nav ul");
    const toggleMenu = document.querySelector(".toggle-menu");

    toggleMenu.addEventListener("click", () => {
        nav.classList.toggle("show");
    });
});

document.addEventListener("DOMContentLoaded", function () {
    const toggleMenu = document.querySelector(".toggle-menu");
    const navMenu = document.querySelector("#nav-links");

    // When the hamburger is clicked
    toggleMenu.addEventListener("click", () => {
        navMenu.classList.toggle("show"); // Toggle visibility of the menu
        toggleMenu.classList.toggle("active"); // Change hamburger to cross icon
    });
});