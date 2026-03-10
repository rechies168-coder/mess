document.getElementById('regBtn').addEventListener('click', () => {
    const email = document.getElementById('email').value;
    const user = document.getElementById('username').value;
    const pass = document.getElementById('password').value;
    const errorDiv = document.getElementById('error-msg');

    fetch('/api/register', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({email, username: user, password: pass})
    })
    .then(r => r.json())
    .then(data => {
        if(data.success) {
            alert("Регистрация успешна!");
            window.location.href = '/login';
        } else errorDiv.innerText = data.error;
    });
});