const floatingContainer = document.getElementById('floating_container')

function setFloating(element) {
    let dragging = false, offsetX, offsetY

    element.addEventListener("mousedown", (e) => {
        dragging = true
        offsetX = e.clientX - element.offsetLeft
        offsetY = e.clientY - element.offsetTop

        playSound(Sounds.PICK, volume=0.3)
    })

    document.addEventListener('mousemove', (e) => {
        if (dragging) {
            element.style.left = `${e.clientX - offsetX}px`
            element.style.top = `${e.clientY - offsetY}px`
        }
    })

    document.addEventListener('mouseup', (e) => {
        dragging = false
    })
}