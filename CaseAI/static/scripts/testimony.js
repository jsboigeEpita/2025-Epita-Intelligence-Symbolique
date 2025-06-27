let testimonyAgent = null
let isAsking = false

function setTestimonyAvatar(url) {
    testimonyAgentImage.style.backgroundImage = `url('${url}')`
}

function createTestimony() {
    setFloating(testimony)
    setTestimonyAvatar(`static/images/unknown.png`)
}

function setTestimonyAgent(agent) {
    if (isAsking)
        return

    setTestimonyAvatar(`static/assets/tokens/character/${agent.avatar}.png`)
    testimonyAgent = agent

    if (backend.suspects[agent.suspect.name]) {
        let messages = backend.suspects[agent.suspect.name].messages
        testimonyText.innerText = messages[messages.length - 1].content
    }
    else
        testimonyText.innerText = 'Hey, please ask me anything.'
}

testimonyInput.addEventListener('keydown', async (e) => {
    if (event.key !== 'Enter' || testimonyAgent === null)
        return

    let question = testimonyInput.value
    testimonyInput.value = ''

    isAsking = true
    testimonyInput.classList.add('hidden')

    testimonyText.innerText = 'Answering...'

    let resp = await ask(question, testimonyAgent.suspect.name)

    if (resp.alibi && !testimonyAgent.alibiGiven) {
        testimonyAgent.alibiGiven = true

        createNote('alibi', testimonyAgent.suspect.name, resp.alibi)
    }

    for (let obs of resp.new_obs) {
        createNote('observation', testimonyAgent.suspect.name, obs)
    }
    
    if (resp.trash) {
        createNote('trash', testimonyAgent.suspect.name, resp.trash)
    }

    testimonyText.innerText = resp.response

    testimonyInput.classList.remove('hidden')
    isAsking = false

    playSound(Sounds.GIBBERISH_0)

    if (!backend.watson_found)
    {
        if (await watsonHasFound()) {
            createNote('watson', null, null)
            backend.watson_found = true
        }
    }
})

testimonyAccuse.onclick = () => {
    if (testimonyAgent === null)
        return

    if (testimonyAgent.suspect.name === backend.plot.solution.murderer) {
        setSubtitle('Well done Sherlock!')
    } else {
        setSubtitle('You jailed an innocent!')
    }

    endText.innerText = `${backend.end_speech}`
    
    backend.ended = true

    setView(Views.END)
}

