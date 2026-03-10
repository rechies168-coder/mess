document.getElementById('loginBtn').addEventListener('click', () => {
    const user = document.getElementById('username').value;
    const pass = document.getElementById('password').value;
    const errorDiv = document.getElementById('error-msg');

    fetch('/api/login', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({username: user, password: pass})
    })
    .then(r => r.json())
    .then(data => {
        if(data.success) window.location.href = '/';
        else errorDiv.innerText = data.error;
    })
    .catch(() => errorDiv.innerText = "Сервер не отвечает");
});