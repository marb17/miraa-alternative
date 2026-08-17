// Below declares all used variables
let StartUp = false;
let inpage3=false;
let response;
let data;
let lyric;

const circlec = document.getElementById("circlecontainer");
const appbackground=document.getElementById("app");
const circleout=document.getElementById("circleoutline");
const clickanywhere = document.getElementById("clickanywheretostart");
const titletextcontainer = document.getElementById("titlecontainer");
const lyrics = document.getElementById("lyrics");
// Above declares all used variables

// Below are all the functions that will be used

function delay(ms){
    return new Promise(resolve => setTimeout(resolve, ms));
} // function to create delay in milliseconds


// this is a temporary way to go back to the first page as i havent added a proper way to return. Terrible functionality btw just reload the page when u come
function returnpage1() {
        window.location.href="page1.html";
}

function returnpage2() {
    window.location.href="page2.html";
}

function returnpage3() {
    window.location.href="page3.html";
    inpage3=true;
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

async function EnterPage3(){
    try {
        response = await fetch('../../../test_data/output/Haikei Shounenyo - Hump Back.json');
        data = await response.json();
        lyric = data.translated_lyrics;

        console.log(lyric);
    } catch (error) {
        console.error("Failed to load lyrics:", error);
    }
    lyrics.textContent =lyric;
}