// Views
const mainView = document.getElementById('main_view')
const gameView = document.getElementById('game_view')
const boardView = document.getElementById('board_view')
const emptyView = document.getElementById('empty_view')
const endView = document.getElementById('end_view')

// Global
const subtitle = document.getElementById('subtitle')

// Main View
const playButton = document.getElementById('play_button')
const rulesPanel = document.getElementById('rules')
const buttonsPanel = document.getElementById('buttons')
const settingsPanel = document.getElementById('settings')
const phaserContainer = document.getElementById('phaser_container')

const testimony = document.getElementById('testimony')
const testimonyAgentImage = document.getElementById('testimony_header').children[1]
const testimonyInput = document.getElementById('testimony_input')
const testimonyText = document.getElementById('testimony_text')
const testimonyAccuse = document.getElementById('testimony_accuse_button')
const endText = document.getElementById('end_text')

// Board View
const newspaper = document.getElementById('newspaper')
const newspaperText = document.getElementById('newspaper_text')
const newspaperPicture = document.getElementById('newspaper_picture')

// Globals variables
let gameRunning = false

// ------- UTILS --------

function isGameRunning() {
    return gameRunning
}

function setSubtitle(str) {
    subtitle.innerText = str
}