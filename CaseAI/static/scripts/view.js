let currentView = null


// Enum-like structure
let Views = {
    MAIN: { name: 'MAIN', dom: mainView },
    GAME: { name: 'GAME', dom: gameView },
    BOARD: { name: 'BOARD', dom: boardView },
    EMPTY: { name: 'EMPTY', dom: emptyView },
    END: { name: 'END', dom: endView }
}

for (let vkey in Views)
    Views[vkey].callbacks = []

function attachElementToView(element, view) {
    view.dom.appendChild(element)
}

function addViewCallback(view, callback) {
    view.callbacks.push(callback)
}

function setView(view) {
    if (currentView !== null) {
        currentView.dom.classList.add('hidden')
    }

    view.dom.classList.remove('hidden')
    currentView = view   

    for (let callback of view.callbacks) callback()
}