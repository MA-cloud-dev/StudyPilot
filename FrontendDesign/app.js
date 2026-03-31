document.addEventListener('DOMContentLoaded', () => {
    
    const navItems = document.querySelectorAll('.nav-item');
    const views = document.querySelectorAll('.view');
    const appContainer = document.getElementById('app-container');
    
    // Hash routing
    function handleRoute() {
        let hash = window.location.hash.substring(1) || 'macro-plan';
        
        // 按照用户需求，无论在哪个视图，都保留左侧全局导航栏
        appContainer.classList.remove('hide-sidebar');
        
        // Update nav active state
        navItems.forEach(item => {
            if (item.dataset.view === hash) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });
        
        // Update view visibility
        views.forEach(view => {
            if (view.id === 'view-' + hash) {
                view.classList.add('active');
            } else {
                view.classList.remove('active');
            }
        });
    }
    
    window.addEventListener('hashchange', handleRoute);
    handleRoute();
    
    // UI Chat interaction for Macro Plan Hub
    const planInput = document.getElementById('plan-chat-input');
    const planBtn = document.getElementById('plan-btn-send');
    const planChat = document.getElementById('plan-chat-messages');
    
    function sendPlanMsg() {
        if(!planInput.value.trim()) return;
        const msg = document.createElement('div');
        msg.className = 'message user';
        msg.innerHTML = `<div class="avatar-me">Me</div><div class="message-bubble user-bubble">${planInput.value}</div>`;
        planChat.appendChild(msg);
        planInput.value = '';
        planChat.scrollTop = planChat.scrollHeight;
        
        setTimeout(() => {
            const aiMsg = document.createElement('div');
            aiMsg.className = 'message system';
            aiMsg.innerHTML = `<div class="avatar-ai">AI</div><div class="message-bubble system-bubble">计划正在生成中，请稍候...</div>`;
            planChat.appendChild(aiMsg);
            planChat.scrollTop = planChat.scrollHeight;
        }, 600);
    }
    planBtn.addEventListener('click', sendPlanMsg);
    planInput.addEventListener('keypress', e => e.key === 'Enter' && sendPlanMsg());
    
    // UI Chat interaction for Study Workbench
    const studyInput = document.getElementById('study-chat-input');
    const studyBtn = document.getElementById('study-btn-send');
    const studyChat = document.getElementById('study-chat-messages');
    
    function sendStudyMsg() {
        if(!studyInput.value.trim()) return;
        const msg = document.createElement('div');
        msg.className = 'message user';
        msg.innerHTML = `<div class="avatar-me">Me</div><div class="message-bubble user-bubble">${studyInput.value}</div>`;
        studyChat.appendChild(msg);
        studyInput.value = '';
        studyChat.scrollTop = studyChat.scrollHeight;
        
        setTimeout(() => {
            const aiMsg = document.createElement('div');
            aiMsg.className = 'message system';
            aiMsg.innerHTML = `<div class="avatar-ai">AI</div><div class="message-bubble system-bubble">我在，有关于 Series 的其它疑问吗？</div>`;
            studyChat.appendChild(aiMsg);
            studyChat.scrollTop = studyChat.scrollHeight;
        }, 1000);
    }
    studyBtn.addEventListener('click', sendStudyMsg);
    studyInput.addEventListener('keypress', e => e.key === 'Enter' && sendStudyMsg());

    // Single select for assessment options
    const options = document.querySelectorAll('.option-item');
    const submitBtn = document.getElementById('btn-submit-answer');
    
    options.forEach(opt => {
        opt.addEventListener('click', () => {
            options.forEach(o => o.classList.remove('selected'));
            opt.classList.add('selected');
            submitBtn.disabled = false;
        });
    });
    
    // Upload interaction
    const uploadZone = document.getElementById('upload-zone');
    const demoUpload = document.getElementById('demo-uploading-file');
    const demoProgress = document.getElementById('demo-upload-progress');
    const demoStatus = document.getElementById('demo-upload-status');
    
    if(uploadZone) {
        uploadZone.addEventListener('click', () => {
            demoUpload.style.display = 'flex';
            let p = 0;
            demoStatus.innerText = '上传中...';
            const inv = setInterval(() => {
                p += 15;
                demoProgress.style.width = p + '%';
                if(p >= 100) {
                    clearInterval(inv);
                    demoStatus.innerText = '就绪';
                    demoStatus.style.color = 'var(--success)';
                    demoProgress.style.backgroundColor = 'var(--success)';
                }
            }, 300);
        });
    }

});
