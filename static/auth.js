// 显示注册表单
function showRegister() {
    document.getElementById('loginForm').style.display = 'none';
    document.getElementById('registerForm').style.display = 'block';
    refreshCaptcha();
}

// 显示登录表单
function showLogin() {
    document.getElementById('loginForm').style.display = 'block';
    document.getElementById('registerForm').style.display = 'none';
}

// 登录函数
async function login() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    if (!username || !password) {
        alert('请输入用户名和密码');
        return;
    }
    
    try {
        const response = await fetch('/api/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            window.location.href = '/';  // 登录成功后跳转到主页
        } else {
            alert(data.error || '登录失败');
        }
    } catch (error) {
        alert('网络错误，请重试');
    }
}

// 注册函数
async function register() {
    const username = document.getElementById('regUsername').value;
    const password = document.getElementById('regPassword').value;
    const passwordConfirm = document.getElementById('regPasswordConfirm').value;
    const captcha = document.getElementById('captcha').value;
    
    if (!username || !password || !passwordConfirm || !captcha) {
        alert('请填写所有字段');
        return;
    }
    
    if (password !== passwordConfirm) {
        alert('两次输入的密码不一致');
        return;
    }
    
    try {
        const response = await fetch('/api/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password, captcha })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            alert('注册成功，请登录');
            showLogin();
        } else {
            alert(data.error || '注册失败');
            refreshCaptcha(); // 注册失败时刷新验证码
        }
    } catch (error) {
        alert('网络错误，请重试');
        refreshCaptcha();
    }
}

// 获取验证码
async function refreshCaptcha() {
    try {
        const response = await fetch('/api/captcha');
        const data = await response.json();
        document.getElementById('captchaImage').src = data.image;
    } catch (error) {
        alert('获取验证码失败，请重试');
    }
}

// 添加回车键支持
document.addEventListener('DOMContentLoaded', () => {
    // 登录表单回车支持
    document.getElementById('username').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            document.getElementById('password').focus();
        }
    });
    
    document.getElementById('password').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            login();
        }
    });
    
    // 注册表单回车支持
    document.getElementById('regUsername').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            document.getElementById('regPassword').focus();
        }
    });
    
    document.getElementById('regPassword').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            document.getElementById('regPasswordConfirm').focus();
        }
    });
    
    document.getElementById('regPasswordConfirm').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            register();
        }
    });
    
    // 添加验证码输入框的回车键支持
    document.getElementById('captcha').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            register();
        }
    });
}); 