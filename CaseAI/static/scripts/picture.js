const pictureTemplate = document.getElementsByClassName('picture')[0]

function createPicture(agent) {
    let picture = pictureTemplate.cloneNode(true)
    let image = picture.children[0]
    let text = picture.children[1]

    image.style.backgroundImage = `url('static/assets/tokens/character/${agent.avatar}.png')`
    text.innerText = agent.suspect.name

    setFloating(picture)
    picture.classList.remove('hidden')

    attachElementToView(picture, Views.BOARD)
}