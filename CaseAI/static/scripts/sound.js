let Sounds = {
    BACKGROUND : { name: 'background', dom: document.getElementById('sound_background_music') },
    WOOSH : { name: 'woosh', dom: document.getElementById('sound_woosh') },
    PICK : { name: 'pick', dom: document.getElementById('sound_pick') },
    HM : { name: 'hm', dom: document.getElementById('sound_hm') },
    GIBBERISH_0 : { name: 'gibberish0', dom: document.getElementById('sound_gibberish0') },
    HAMMER : { name: 'hammer', dom: document.getElementById('sound_hammer') },
    FOOTSTEPS : { name: 'footsteps', dom: document.getElementById('sound_footsteps') },
}

function playSound(sound, volume = 1) {
    sound.dom.currentTime = 0
    sound.dom.volume = volume
    sound.dom.play()
}

let possibleAmbientSounds = [ [Sounds.HAMMER, 0.5], [Sounds.FOOTSTEPS, 0.8] ]

async function ambientSounds() {
    if (currentView !== null && currentView.name === Views.GAME.name) {
        let [s, v] = possibleAmbientSounds[Math.floor(Math.random() * possibleAmbientSounds.length)]
        playSound(s, v)
    }

    setTimeout(() => {
        ambientSounds()
    }, 30000);
}

ambientSounds()