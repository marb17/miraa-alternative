document.addEventListener("click", Page1ToPage2);
document.addEventListener( "keydown", (keypress) => {
    if (keypress.key === "1") {
        CurrentPage = 1
        goToPage1();
    }
}) // this is a temporary way to go back to the first page as i havent added a proper way to return


document.addEventListener( "keydown", (keypress) => {
    if (keypress.key === "2") {
        CurrentPage = 2;
        goToPage2();
    }
})  // temporary way to go to 2nd page

document.addEventListener( "keydown", (keypress) => {
    if (keypress.key === "3") {
        CurrentPage = 3;
    }
}) //// temporary way to go to third page




if (window.location.pathname.includes("page3.html")) {
    EnterPage3();
}


window.addEventListener('mousemove', (event) => {
    mouseX = event.clientX; //finds cursor x position
    mouseY = event.clientY; //finds cursor y positont
});
if (gridbg) {
    gridmove();
}

if (window.location.pathname.includes("page2.html")) {
    document.addEventListener("keydown", (keypress) => {
        if (keypress.key === "p") {
            if (!searchresults) return;
            searchresults.style.animation =
                "boxExpand 0.6s cubic-bezier(0.7410154978434245, 0.09296875000000004, 0.27351557413736977, 0.795468839009603) forwards";

        }

    });

}