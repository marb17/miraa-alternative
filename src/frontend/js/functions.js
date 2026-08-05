// Below declares all used variables
let StartUp = false;


const circlec = document.getElementById("circlecontainer");
const appbackground=document.getElementById("app");
const circleout=document.getElementById("circleoutline");
const clickanywhere = document.getElementById("clickanywheretostart");
const titletextcontainer = document.getElementById("titlecontainer");
// Above declares all used variables

// Below are all the functions that will be used

function delay(ms){
    return new Promise(resolve => setTimeout(resolve, ms));
} // function to create delay in milliseconds


// this is a temporary way to go back to the first page as i havent added a proper way to return. Terrible functionality btw just reload the page when u come
function returnback() {
        window.location.href="page1.html";
}

// this function starts the transition for the first to second page
async function StartMenuTransition() {
    if (StartUp === true) return;
    console.log("StartMenu");
    StartUp = true;
    circlec.style.transform = "translate(-100%, -50%)";
    appbackground.style.backgroundColor = "#887aab";
    circleout.style.backgroundColor = "#887aab";
    circleout.style.border = "#887aab";
    clickanywhere.style.color="#887aab";
    titletextcontainer.style.opacity = 0;
    await delay(400);
    window.location.href= "page2.html";
}