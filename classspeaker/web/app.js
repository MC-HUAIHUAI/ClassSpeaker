/* 教室小喇叭 · 教师端脚本（无框架，纯原生 JS） */
(function () {
  "use strict";

  var TOKEN_KEY = "classspeaker_token";
  var POLL_MS = 1500;

  var state = {
    token: window.localStorage.getItem(TOKEN_KEY) || "",
    user: null,
    info: null,
    messages: [],
    knownStatus: {},
    messageTimer: null,
    infoTimer: null,
    users: [],
  };

  /* ---------------- 小工具 ---------------- */
  function $(id) {
    return document.getElementById(id);
  }

  function show(el, visible) {
    if (!el) return;
    if (visible) el.classList.remove("hidden");
    else el.classList.add("hidden");
  }

  function toast(text, kind, ms) {
    var wrap = $("toastWrap");
    if (!wrap) return;
    var node = document.createElement("div");
    node.className = "toast" + (kind ? " " + kind : "");
    node.textContent = text;
    wrap.appendChild(node);
    window.setTimeout(function () {
      node.style.opacity = "0";
      window.setTimeout(function () {
        if (node.parentNode) node.parentNode.removeChild(node);
      }, 240);
    }, ms || 3200);
  }

  function setMsg(el, text, kind) {
    if (!el) return;
    el.textContent = text || "";
    el.className = "msg" + (kind ? " " + kind : "");
  }

  function api(path, options) {
    options = options || {};
    var headers = {};
    var init = { method: options.method || "GET", headers: headers };
    if (options.body !== undefined && options.body !== null) {
      headers["Content-Type"] = "application/json";
      init.body = JSON.stringify(options.body);
    }
    if (options.auth !== false && state.token) {
      headers["X-Auth-Token"] = state.token;
    }
    return fetch(path, init).then(function (res) {
      return res.json().catch(function () {
        return {};
      }).then(function (data) {
        if (!res.ok || data.ok === false) {
          var err = new Error(data.error || ("请求失败（HTTP " + res.status + "）"));
          err.status = res.status;
          throw err;
        }
        return data;
      });
    });
  }

  /* ---------------- 顶栏状态 ---------------- */
  function renderClassroom(info) {
    if (!info) return;
    $("classroomName").textContent = info.classroom || "教室";
    $("address").textContent = info.address || "";
  }

  function setOnline(online, text) {
    var dot = $("statusDot");
    var label = $("statusText");
    dot.classList.remove("online", "offline");
    dot.classList.add(online ? "online" : "offline");
    label.textContent = text || (online ? "教室端在线" : "教室端离线");
  }

  /* ---------------- 登录 / 注册 ---------------- */
  function switchTab(name) {
    var tabs = document.querySelectorAll(".tab");
    for (var i = 0; i < tabs.length; i++) {
      tabs[i].classList.toggle("active", tabs[i].getAttribute("data-tab") === name);
    }
    show($("loginForm"), name === "login");
    show($("registerForm"), name === "register");
    setMsg($("authMsg"), "");
  }

  function doLogin(event) {
    event.preventDefault();
    var btn = $("loginBtn");
    btn.disabled = true;
    setMsg($("authMsg"), "正在登录…");
    api("/api/login", {
      method: "POST",
      auth: false,
      body: {
        username: $("loginUser").value.trim(),
        password: $("loginPass").value,
      },
    }).then(function (data) {
      state.token = data.token;
      state.user = data.user;
      window.localStorage.setItem(TOKEN_KEY, data.token);
      setMsg($("authMsg"), "");
      $("loginPass").value = "";
      enterMain();
      toast("登录成功，欢迎 " + (state.user.display_name || state.user.username), "ok");
    }).catch(function (err) {
      setMsg($("authMsg"), err.message, "error");
    }).then(function () {
      btn.disabled = false;
    });
  }

  function doRegister(event) {
    event.preventDefault();
    var pass = $("regPass").value;
    var pass2 = $("regPass2").value;
    if (pass !== pass2) {
      setMsg($("authMsg"), "两次输入的密码不一致", "error");
      return;
    }
    var btn = $("regBtn");
    btn.disabled = true;
    setMsg($("authMsg"), "正在提交…");
    api("/api/register", {
      method: "POST",
      auth: false,
      body: {
        username: $("regUser").value.trim(),
        display_name: $("regName").value.trim(),
        password: pass,
      },
    }).then(function (data) {
      setMsg($("authMsg"), data.message || "提交成功", "ok");
      toast(data.message || "提交成功", "ok", 5000);
      $("regPass").value = "";
      $("regPass2").value = "";
      if (data.status === "approved") {
        switchTab("login");
        $("loginUser").value = $("regUser").value.trim();
      }
    }).catch(function (err) {
      setMsg($("authMsg"), err.message, "error");
    }).then(function () {
      btn.disabled = false;
    });
  }

  function doLogout() {
    api("/api/logout", { method: "POST" }).catch(function () {}).then(function () {
      state.token = "";
      state.user = null;
      window.localStorage.removeItem(TOKEN_KEY);
      stopPolling();
      show($("mainView"), false);
      show($("adminCard"), false);
      show($("logoutBtn"), false);
      show($("authView"), true);
      setMsg($("authMsg"), "已退出登录");
    });
  }

  /* ---------------- 主界面 ---------------- */
  function enterMain() {
    show($("authView"), false);
    show($("mainView"), true);
    show($("logoutBtn"), true);
    var isAdmin = state.user && state.user.role === "admin";
    show($("adminCard"), !!isAdmin);
    if (isAdmin) loadUsers();
    startPolling();
  }

  function startPolling() {
    stopPolling();
    refreshMessages();
    state.messageTimer = window.setInterval(refreshMessages, POLL_MS);
  }

  function stopPolling() {
    if (state.messageTimer) {
      window.clearInterval(state.messageTimer);
      state.messageTimer = null;
    }
  }

  function doSend() {
    var input = $("contentInput");
    var content = input.value.trim();
    if (!content) {
      setMsg($("sendMsg"), "请输入要发送的内容", "error");
      return;
    }
    var btn = $("sendBtn");
    btn.disabled = true;
    setMsg($("sendMsg"), "正在发送…");
    api("/api/send", { method: "POST", body: { content: content } })
      .then(function (data) {
        input.value = "";
        updateCounter();
        setMsg($("sendMsg"), "已发送，等待教室端“确认收到”", "ok");
        toast("消息已发送到教室", "ok");
        if (data.message) {
          state.messages.unshift(data.message);
          state.knownStatus[data.message.id] = data.message.status;
          renderMessages();
        }
        refreshMessages();
      })
      .catch(function (err) {
        setMsg($("sendMsg"), err.message, "error");
      })
      .then(function () {
        btn.disabled = false;
      });
  }

  function statusText(status) {
    return status === "received" ? "教室已确认收到" : "等待教室确认";
  }

  function renderMessages() {
    var list = $("messageList");
    list.innerHTML = "";
    if (!state.messages.length) {
      var empty = document.createElement("li");
      empty.className = "empty";
      empty.textContent = "暂无记录";
      list.appendChild(empty);
      return;
    }
    state.messages.forEach(function (msg) {
      var li = document.createElement("li");

      var head = document.createElement("div");
      head.className = "item-head";

      var chip = document.createElement("span");
      chip.className = "chip " + (msg.status === "received" ? "received" : "pending");
      chip.textContent = statusText(msg.status);

      var meta = document.createElement("span");
      meta.className = "item-meta";
      meta.textContent = (msg.sender_name ? msg.sender_name + " · " : "") +
        (msg.created_at || "") +
        (msg.received_at ? "　确认于 " + msg.received_at : "");

      head.appendChild(chip);
      head.appendChild(meta);

      var body = document.createElement("div");
      body.className = "item-body";
      body.textContent = msg.content || "";

      li.appendChild(head);
      li.appendChild(body);
      list.appendChild(li);
    });
  }

  function refreshMessages() {
    if (!state.token) return;
    api("/api/messages?limit=100").then(function (data) {
      var messages = data.messages || [];
      messages.forEach(function (msg) {
        var before = state.knownStatus[msg.id];
        if (before === "pending" && msg.status === "received") {
          toast("教室已确认收到：" + (msg.content || "").slice(0, 24), "ok", 4000);
        }
        state.knownStatus[msg.id] = msg.status;
      });
      state.messages = messages;
      renderMessages();
      setOnline(true);
    }).catch(function (err) {
      if (err.status === 401 || err.status === 403) {
        toast(err.message, "warn");
        doLogout();
        return;
      }
      setOnline(false);
    });
  }

  function refreshInfo() {
    api("/api/info", { auth: false }).then(function (info) {
      state.info = info;
      renderClassroom(info);
      setOnline(true);
    }).catch(function () {
      setOnline(false, "教室端已断开");
    });
  }

  function updateCounter() {
    var value = $("contentInput").value || "";
    $("counter").textContent = value.length + " / 1000";
  }

  /* ---------------- 管理员：账号管理 ---------------- */
  function loadUsers() {
    api("/api/users").then(function (data) {
      state.users = data.users || [];
      renderUsers();
    }).catch(function (err) {
      toast(err.message, "error");
    });
  }

  function userAction(path, userId, confirmText, okText) {
    if (confirmText && !window.confirm(confirmText)) return;
    api(path, { method: "POST", body: { user_id: userId } }).then(function (data) {
      toast(data.message || okText || "操作成功", "ok");
      loadUsers();
    }).catch(function (err) {
      toast(err.message, "error");
    });
  }

  function renderUsers() {
    var list = $("userList");
    list.innerHTML = "";
    if (!state.users.length) {
      var empty = document.createElement("li");
      empty.className = "empty";
      empty.textContent = "暂无账号";
      list.appendChild(empty);
      return;
    }
    state.users.forEach(function (user) {
      var li = document.createElement("li");

      var head = document.createElement("div");
      head.className = "item-head";

      var left = document.createElement("div");
      var name = document.createElement("strong");
      name.textContent = user.display_name || user.username;
      left.appendChild(name);
      var meta = document.createElement("div");
      meta.className = "item-meta";
      meta.textContent = "@" + user.username +
        (user.status === "approved" && user.last_login
          ? "　最近登录 " + user.last_login : "");
      left.appendChild(meta);

      var chips = document.createElement("div");
      chips.className = "row";
      chips.style.marginTop = "0";
      chips.style.gap = "6px";

      var chip = document.createElement("span");
      chip.className = "chip " + user.status;
      chip.textContent = user.status === "approved" ? "已启用"
        : (user.status === "pending" ? "待审批" : "已拒绝");
      chips.appendChild(chip);

      if (user.role === "admin") {
        var adminChip = document.createElement("span");
        adminChip.className = "chip admin";
        adminChip.textContent = "管理员";
        chips.appendChild(adminChip);
      }

      head.appendChild(left);
      head.appendChild(chips);
      li.appendChild(head);

      var actions = document.createElement("div");
      actions.className = "user-actions";

      if (user.status !== "approved") {
        var approve = document.createElement("button");
        approve.className = "mini primary";
        approve.textContent = "批准";
        approve.onclick = function () {
          userAction("/api/users/approve", user.id, null, "已批准");
        };
        actions.appendChild(approve);
      }
      if (user.status === "pending") {
        var reject = document.createElement("button");
        reject.className = "mini";
        reject.textContent = "拒绝";
        reject.onclick = function () {
          userAction("/api/users/reject", user.id, "确定拒绝该账号？", "已拒绝");
        };
        actions.appendChild(reject);
      }
      if (!(state.user && state.user.id === user.id)) {
        var del = document.createElement("button");
        del.className = "mini";
        del.textContent = "删除";
        del.onclick = function () {
          userAction("/api/users/delete", user.id,
            "确定删除账号 " + user.username + "？", "已删除");
        };
        actions.appendChild(del);
      }

      li.appendChild(actions);
      list.appendChild(li);
    });
  }

  /* ---------------- 初始化 ---------------- */
  function bind() {
    var tabs = document.querySelectorAll(".tab");
    for (var i = 0; i < tabs.length; i++) {
      (function (tab) {
        tab.onclick = function () {
          switchTab(tab.getAttribute("data-tab"));
        };
      })(tabs[i]);
    }
    $("loginForm").onsubmit = doLogin;
    $("registerForm").onsubmit = doRegister;
    $("logoutBtn").onclick = doLogout;
    $("sendBtn").onclick = doSend;
    $("refreshBtn").onclick = function () {
      refreshMessages();
      loadUsersWhenAdmin();
    };
    $("reloadUsersBtn").onclick = loadUsers;
    $("contentInput").oninput = updateCounter;
    $("contentInput").onkeydown = function (event) {
      if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
        doSend();
      }
    };
  }

  function loadUsersWhenAdmin() {
    if (state.user && state.user.role === "admin") loadUsers();
  }

  function boot() {
    bind();
    updateCounter();
    refreshInfo();
    state.infoTimer = window.setInterval(function () {
      if (!state.token) refreshInfo();
    }, 5000);

    if (state.token) {
      api("/api/me").then(function (data) {
        state.user = data.user;
        renderClassroom({ classroom: data.classroom, address: data.address });
        enterMain();
      }).catch(function () {
        state.token = "";
        window.localStorage.removeItem(TOKEN_KEY);
        show($("authView"), true);
      });
    } else {
      show($("authView"), true);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
