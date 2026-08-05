document.addEventListener("click", StartMenuTransition);
document.addEventListener( "keydown", (keypress) => {
    if (keypress.key === "Escape") {
        returnback();
    }
}) // this is a temporary way to go back to the first page as i havent added a proper way to return