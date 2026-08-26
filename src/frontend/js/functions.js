// Below declares all used variables
let StartUp = false;
let inpage3=false;
let inpage1 = true;
let inpage2 = false;
let response;
let data;
let lyricArray;
let formattedLyrics;
let mouseX = window.innerWidth / 2;
let mouseY = window.innerHeight / 2;
let gridX = window.innerWidth / 2;
let gridY = window.innerHeight / 2;
let CurrentPage = 1;

const circlec = document.getElementById("circlecontainer");
const appbackground=document.getElementById("app");
const circleout=document.getElementById("circleoutline");
const clickanywhere = document.getElementById("clickanywheretostart");
const titletextcontainer = document.getElementById("titlecontainer");
const lyrics = document.getElementById("lyrics");
const gridbg = document.getElementById("grid");
const gridease = 0.01; // this value causes the grid movement to lag behind (for smoothness)
const searchinput = document.getElementById("searchinput");
const searchresults = document.getElementById("searchresults");
// Above declares all used variables

function gridmove() {
    gridX += (mouseX - gridX)*gridease;
    gridY += (mouseY - gridY)*gridease;

    gridbg.style.transform = `translate3d(${gridX}px, ${ gridY}px, 0) translate(-50%, -50%)`;
    requestAnimationFrame(gridmove);
}

function Page1ToPage2(){
    if (!window.location.pathname.includes("page1.html")) return;
    goToPage2();
}

function goToPage1() {
    window.location.href="page1.html";
}

function goToPage2(){
    window.location.href="page2.html";
}

function goToPage3() {
    window.location.href = "page3.html";
}































// Below are all the functions that will be used

function delay(ms){
    return new Promise(resolve => setTimeout(resolve, ms));
} // function to create delay in milliseconds


// this function starts the transition for the first to second page
// async function StartMenuTransition() {
//    if (StartUp === true) return;
//    console.log("StartMenu");
//    StartUp = true;
//    circlec.style.transform = "translate(-100%, -50%)";
//    appbackground.style.backgroundColor = "#887aab";
//    circleout.style.backgroundColor = "#887aab";
//    circleout.style.border = "#887aab";
 //   clickanywhere.style.color= "#887aab";
 //   titletextcontainer.style.opacity = 0;
 //   await delay(400);
//    window.location.href= "page2.html";


async function EnterPage3(){
    try {
        response = await fetch('../../../test_data/output/Haikei Shounenyo - Hump Back.json');
        data = await response.json();
        lyricArray = data.translated_lyrics;

        console.log(lyricArray);
        formattedLyrics = lyricArray.join('<br>')+ '<br><br>&nbsp;';
    } catch (error) {

        console.error("Failed to load lyrics:", error);
    }
    lyrics.innerHTML = formattedLyrics;
} // for future reference : Basically, this line of code above takes the text from the json file's array thing
// then it combined all of the items in the array, and adds a <br> between each single item (in this case on line of lyrics)
// then the .innerHTML is used to treat the entire line of every item and <br> as a line of html code, thus causing
// all of the lines to be neatly formatted and separated.