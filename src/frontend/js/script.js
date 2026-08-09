document.addEventListener("click", StartMenuTransition);
document.addEventListener( "keydown", (keypress) => {
    if (keypress.key === "1") {
        returnpage1();
    }
}) // this is a temporary way to go back to the first page as i havent added a proper way to return


document.addEventListener( "keydown", (keypress) => {
    if (keypress.key === "2") {
        returnpage2();
    }
})  // temporary way to go to 2nd page

document.addEventListener( "keydown", (keypress) => {
    if (keypress.key === "3") {
        returnpage3();
    }
}) // temporary way to go to third page