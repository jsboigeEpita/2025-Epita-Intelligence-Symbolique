const apiKeyInput = document.getElementById('api_key_input')

// Without trailing /
const baseUrl = "";

apiKeyInput.addEventListener('change', () => {
    backend.model.API_KEY = apiKeyInput.value
    console.log(`API key was changed to '${backend.model.API_KEY}'.`)
})

