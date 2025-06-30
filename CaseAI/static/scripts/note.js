const noteTemplate = document.getElementsByClassName('note')[0]

let watsonMessages = [
    "I\'ve cracked it.\n\nNow let\'s see if you can keep up, detective!",
    "The mystery's solved... on my end.\n\nYour turn to catch up!",
    "Elementary, my friend.\n\nWell... for me, at least. Time to gather your clues!",
    "I've got the answer.\n\nLet's see if your brain's as sharp as your hat."
]

function createNote(type, who, content) {
    console.log(type)

    let note = noteTemplate.cloneNode(true)
    let title = note.children[0]
    let text = note.children[1]

    note.classList.add(`note-${type}`)

    if (type === 'alibi') {
        title.innerText = `ALIBI of ${who}`
        text.innerText = content;
    } else if (type === 'observation') {
        title.innerText = `OBSERVATION of ${who}`
        text.innerText = content;
    } else if (type === 'trash') {
        title.innerText = `MISC of ${who}`
        text.innerText = content;
    } else if (type === 'watson') {
        title.innerText = `MESSAGE from Watson`
        text.innerText = watsonMessages[Math.floor(Math.random() * watsonMessages.length)]
    }

    setFloating(note)
    note.classList.remove('hidden')

    attachElementToView(note, Views.BOARD)
}