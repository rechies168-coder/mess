let currentRoomId = null;
let myName = "";
let mediaRecorder;
let chunks = [];

// 1. Загрузка профиля
function initMe() {
    fetch('/api/me').then(r => r.json()).then(u => {
        myName = u.username;
        document.getElementById('my-av').src = u.avatar;
        document.getElementById('my-name').innerText = u.username;
        document.getElementById('my-user').innerText = '@' + u.username;
        loadRooms();
    });
}

// 2. Аватарка
document.getElementById('avatarInput').onchange = (e) => {
    const fd = new FormData();
    fd.append('avatar', e.target.files[0]);
    fetch('/api/profile/update', {method: 'POST', body: fd})
        .then(r => r.json()).then(data => {
            if(data.success) document.getElementById('my-av').src = data.avatar_url;
        });
};

// 3. Поиск и чаты
document.getElementById('searchInput').oninput = (e) => {
    const q = e.target.value;
    if(!q) return loadRooms();
    fetch('/api/users/search?q='+q).then(r => r.json()).then(users => {
        document.getElementById('rooms-list').innerHTML = users.map(u => `
            <div class="list-item" onclick="startChat('${u.username}')">${u.username}</div>
        `).join('');
    });
};

function loadRooms() {
    fetch('/api/rooms').then(r => r.json()).then(rooms => {
        document.getElementById('rooms-list').innerHTML = rooms.map(r => `
            <div class="list-item" onclick="openChat(${r.id},'${r.name}')"><b>${r.name}</b></div>
        `).join('');
    });
}

window.startChat = (name) => {
    fetch('/api/chat/start/'+name, {method:'POST'}).then(r => r.json()).then(data => {
        openChat(data.room_id, data.name);
        loadRooms();
    });
};

window.openChat = (id, name) => {
    currentRoomId = id;
    document.getElementById('chat-header').innerText = name;
    document.getElementById('chat-header').style.display = 'block';
    document.getElementById('input-bar').style.display = 'flex';
    loadMessages();
};

// 4. Сообщения и Голосовые
function loadMessages() {
    if(!currentRoomId) return;
    fetch('/api/messages/'+currentRoomId).then(r => r.json()).then(msgs => {
        document.getElementById('messages').innerHTML = msgs.map(m => `
            <div class="msg ${m.username === myName ? 'my' : 'other'}">
                ${m.text ? `<div>${m.text}</div>` : ''}
                ${m.voice ? `<audio src="${m.voice}" controls></audio>` : ''}
                <div class="time">${m.time}</div>
            </div>
        `).join('');
        const d = document.getElementById('messages'); d.scrollTop = d.scrollHeight;
    });
}

document.getElementById('sendBtn').onclick = () => {
    const text = document.getElementById('msgInput').value;
    if(!text) return;
    const fd = new FormData(); fd.append('text', text);
    fetch('/api/messages/'+currentRoomId, {method:'POST', body:fd}).then(() => {
        document.getElementById('msgInput').value = ''; loadMessages();
    });
};

const mic = document.getElementById('micBtn');
mic.onmousedown = () => {
    navigator.mediaDevices.getUserMedia({audio:true}).then(s => {
        mediaRecorder = new MediaRecorder(s);
        mediaRecorder.start();
        mic.classList.add('recording');
        chunks = [];
        mediaRecorder.ondataavailable = e => chunks.push(e.data);
    });
};
mic.onmouseup = () => {
    if(!mediaRecorder) return;
    mediaRecorder.stop();
    mic.classList.remove('recording');
    mediaRecorder.onstop = () => {
        const fd = new FormData();
        fd.append('voice', new Blob(chunks, {type:'audio/webm'}));
        fetch('/api/messages/'+currentRoomId, {method:'POST', body:fd}).then(() => loadMessages());
    };
};

// 5. UI Элементы
document.getElementById('openSettings').onclick = () => document.getElementById('settings').classList.add('active');
document.getElementById('closeSettings').onclick = () => document.getElementById('settings').classList.remove('active');
document.getElementById('emojiBtn').onclick = () => {
    const el = document.getElementById('emojis');
    el.style.display = el.style.display === 'flex' ? 'none' : 'flex';
};
document.querySelectorAll('.emoji').forEach(e => {
    e.onclick = () => {
        document.getElementById('msgInput').value += e.innerText;
        document.getElementById('emojis').style.display = 'none';
    };
});

initMe();
setInterval(loadMessages, 3000);