/**
 * Livebox Call Monitor — bundled Lovelace card
 *
 * A single card that shows the call log (with per-row "add contact") AND a
 * full contacts CRUD manager, all native inside Home Assistant. It reads
 * sensor.*_call_log and calls the integration services
 * (livebox_callmon.add_contact / edit_contact / delete_contact).
 *
 * Config:
 *   type: custom:livebox-callmon-card
 *   entity: sensor.landline_livebox_landline_call_log   # your call_log sensor
 */

class LiveboxCallmonCard extends HTMLElement {
  setConfig(config) {
    if (!config.entity) throw new Error("Set 'entity' to your call_log sensor");
    this._config = config;
    this._tab = "log";
    this._tag = "other";
    this._editKey = null;
    this.attachShadow({ mode: "open" });
  }

  set hass(hass) {
    this._hass = hass;
    // Do NOT re-render while the user has the add/edit form open — a poll-driven
    // re-render would wipe the form mid-typing (the "flashes then disappears" bug).
    if (this._formOpen) return;
    this._render();
  }

  getCardSize() { return 8; }

  _calls() {
    const st = this._hass.states[this._config.entity];
    return (st && st.attributes && st.attributes.calls) || [];
  }

  _contacts() {
    // Read the REAL stored contacts exposed by the integration on the sensor.
    const st = this._hass.states[this._config.entity];
    const list = (st && st.attributes && st.attributes.contacts) || [];
    return [...list].sort((a, b) => (a.name||"").localeCompare(b.name||""));
  }

  _svc(method, data) {
    return this._hass.callService("livebox_callmon", method, data);
  }

  _render() {
    if (!this._hass) return;
    const calls = this._calls();
    const missed = calls.filter(c => c.direction === "missed").length;
    const inc = calls.filter(c => c.direction === "incoming").length;
    const out = calls.filter(c => c.direction === "outgoing").length;

    const TAGCOL = { family:"#30a46c", work:"#0091ff", spam:"#e5484d", other:"#8b98a9" };
    const ico = d => d==="missed" ? "⚠️" : d==="outgoing" ? "📱" : "📞";

    const logRows = calls.length ? calls.map(c => {
      const tag = c.tag || "";
      const hasName = !!c.name;
      return `
      <div class="row ${tag==='spam'?'spam':''}">
        <div class="ic ${c.direction}">${ico(c.direction)}</div>
        <div class="mid">
          <div class="nm">${this._esc(hasName ? c.name : c.number)}
            ${['spam','family','work'].includes(tag) ? `<span class="badge" style="background:${TAGCOL[tag]}22;color:${TAGCOL[tag]}">${tag}</span>` : ''}</div>
          <div class="sub">${hasName ? this._esc(c.number) : c.direction}</div>
        </div>
        <div class="meta">${c.time_display || ''}${c.duration>0?`<br>${Math.floor(c.duration/60)}m ${c.duration%60}s`:''}</div>
        ${hasName ? '' : `<button class="mini" data-add="${this._esc(c.number)}">＋ name</button>`}
      </div>`;
    }).join("") : `<div class="empty">No calls logged yet.</div>`;

    const contactRows = this._contacts().length ? this._contacts().map(c => `
      <div class="row">
        <div class="av" style="background:${TAGCOL[c.tag]||TAGCOL.other}">${this._initials(c.name)}</div>
        <div class="mid"><div class="nm">${this._esc(c.name)}</div><div class="sub">${this._esc(c.number)}</div></div>
        <span class="badge" style="background:${(TAGCOL[c.tag]||TAGCOL.other)}22;color:${TAGCOL[c.tag]||TAGCOL.other}">${c.tag}</span>
        <button class="iconbtn" data-edit='${JSON.stringify(c)}'>✎</button>
        <button class="iconbtn" data-del="${this._esc(c.number)}">🗑</button>
      </div>`).join("") : `<div class="empty">No contacts yet. Add one below or tap “＋ name” on a call.</div>`;

    this.shadowRoot.innerHTML = `
    <style>
      :host{--fg:var(--primary-text-color);--dim:var(--secondary-text-color);--line:var(--divider-color);--acc:var(--primary-color);}
      ha-card{padding:14px;}
      .tabs{display:flex;gap:8px;margin-bottom:14px;}
      .tab{flex:1;text-align:center;padding:9px;border-radius:10px;cursor:pointer;background:var(--secondary-background-color);color:var(--dim);font-weight:600;}
      .tab.on{background:var(--acc);color:#fff;}
      .stats{display:flex;gap:8px;margin-bottom:12px;}
      .stat{flex:1;text-align:center;border:1px solid var(--line);border-radius:12px;padding:8px;}
      .stat .n{font-size:20px;font-weight:700;} .stat .l{font-size:11px;color:var(--dim);text-transform:uppercase;}
      .stat.m .n{color:#e5484d;}.stat.i .n{color:#30a46c;}.stat.o .n{color:#0091ff;}
      .row{display:flex;align-items:center;gap:10px;padding:10px 6px;border-bottom:1px solid var(--line);}
      .row:last-child{border-bottom:none;}
      .row.spam{background:rgba(229,72,77,.07);border-radius:8px;}
      .ic,.av{width:36px;height:36px;border-radius:50%;flex:none;display:flex;align-items:center;justify-content:center;font-size:15px;}
      .ic.missed{background:rgba(229,72,77,.15);}.ic.incoming{background:rgba(48,164,108,.15);}.ic.outgoing{background:rgba(0,145,255,.15);}
      .av{color:#fff;font-weight:700;}
      .mid{flex:1;min-width:0;}.nm{font-weight:600;display:flex;align-items:center;gap:6px;}.sub{font-size:12px;color:var(--dim);}
      .badge{font-size:10px;font-weight:700;text-transform:uppercase;padding:2px 7px;border-radius:999px;}
      .meta{text-align:right;font-size:12px;color:var(--dim);white-space:nowrap;}
      .mini{border:1px solid var(--acc);color:var(--acc);background:transparent;border-radius:8px;padding:5px 9px;cursor:pointer;font-size:12px;white-space:nowrap;}
      .iconbtn{border:1px solid var(--line);background:var(--secondary-background-color);color:var(--dim);border-radius:8px;width:32px;height:32px;cursor:pointer;}
      .empty{padding:24px;text-align:center;color:var(--dim);}
      .form{margin-top:12px;border-top:1px solid var(--line);padding-top:12px;display:none;}
      .form.show{display:block;}
      .form input{width:100%;box-sizing:border-box;margin-bottom:8px;padding:9px;border-radius:8px;border:1px solid var(--line);background:var(--secondary-background-color);color:var(--fg);}
      .tagrow{display:flex;gap:6px;margin-bottom:8px;}
      .tagrow .t{flex:1;text-align:center;padding:7px;border-radius:8px;border:1px solid var(--line);cursor:pointer;font-size:12px;color:var(--dim);}
      .tagrow .t.sel{color:#fff;border-color:transparent;}
      .frow{display:flex;gap:8px;}
      .btn{flex:1;padding:9px;border-radius:8px;border:none;cursor:pointer;font-weight:600;}
      .btn.p{background:var(--acc);color:#fff;}.btn.g{background:var(--secondary-background-color);color:var(--fg);}
    </style>
    <ha-card>
      <div class="tabs">
        <div class="tab ${this._tab==='log'?'on':''}" id="t-log">📞 Call Log</div>
        <div class="tab ${this._tab==='contacts'?'on':''}" id="t-contacts">📇 Contacts</div>
      </div>
      ${this._tab==='log' ? `
        <div class="stats">
          <div class="stat"><div class="n">${calls.length}</div><div class="l">Total</div></div>
          <div class="stat m"><div class="n">${missed}</div><div class="l">Missed</div></div>
          <div class="stat i"><div class="n">${inc}</div><div class="l">In</div></div>
          <div class="stat o"><div class="n">${out}</div><div class="l">Out</div></div>
        </div>
        <div id="list">${logRows}</div>
      ` : `
        <div id="list">${contactRows}</div>
        <button class="btn p" id="showadd" style="margin-top:12px;">＋ Add contact</button>
        <div class="form" id="form">
          <input id="f_name" placeholder="Name">
          <input id="f_number" placeholder="Number">
          <div class="tagrow" id="tagrow">
            <div class="t" data-t="family">Family</div>
            <div class="t" data-t="work">Work</div>
            <div class="t" data-t="spam">Spam</div>
            <div class="t sel" data-t="other">Other</div>
          </div>
          <div class="frow">
            <button class="btn g" id="cancel">Cancel</button>
            <button class="btn p" id="save">Save</button>
          </div>
        </div>
      `}
    </ha-card>`;

    this._wire();
  }

  _wire() {
    const $ = s => this.shadowRoot.querySelector(s);
    const tl = $("#t-log"), tc = $("#t-contacts");
    if (tl) tl.onclick = () => { this._tab="log"; this._render(); };
    if (tc) tc.onclick = () => { this._tab="contacts"; this._render(); };

    // per-row "add name" from a call
    this.shadowRoot.querySelectorAll("[data-add]").forEach(b => {
      b.onclick = () => { this._tab="contacts"; this._editKey=null; this._prefillNumber=b.dataset.add; this._render(); this._openForm(); };
    });
    this.shadowRoot.querySelectorAll("[data-del]").forEach(b => {
      b.onclick = () => { if (confirm("Delete contact?")) this._svc("delete_contact",{number:b.dataset.del}); };
    });
    this.shadowRoot.querySelectorAll("[data-edit]").forEach(b => {
      b.onclick = () => { const c=JSON.parse(b.dataset.edit); this._editKey=c.number; this._tag=c.tag||"other"; this._render(); this._openForm(c); };
    });

    const showadd = $("#showadd");
    if (showadd) showadd.onclick = () => { this._editKey=null; this._openForm(); };
    const cancel = $("#cancel");
    if (cancel) cancel.onclick = () => { this._formOpen = false; $("#form").classList.remove("show"); this._render(); };
    const save = $("#save");
    if (save) save.onclick = () => this._save();
    this.shadowRoot.querySelectorAll("#tagrow .t").forEach(t => {
      t.onclick = () => { this._tag=t.dataset.t; this.shadowRoot.querySelectorAll("#tagrow .t").forEach(x=>x.classList.toggle("sel",x.dataset.t===this._tag)); };
    });
    if (this._prefillNumber) { this._openForm(); const n=$("#f_number"); if(n){n.value=this._prefillNumber;} this._prefillNumber=null; }
  }

  _openForm(c) {
    const $ = s => this.shadowRoot.querySelector(s);
    const f = $("#form"); if (!f) return;
    this._formOpen = true;
    f.classList.add("show");
    if (c) { $("#f_name").value=c.name||""; $("#f_number").value=c.number||""; this._tag=c.tag||"other"; }
    this.shadowRoot.querySelectorAll("#tagrow .t").forEach(x=>x.classList.toggle("sel",x.dataset.t===this._tag));
    const nm=$("#f_name"); if(nm) nm.focus();
  }

  _save() {
    const $ = s => this.shadowRoot.querySelector(s);
    const name=$("#f_name").value.trim(), number=$("#f_number").value.trim();
    if (!name || !number) { alert("Name and number required"); return; }
    if (this._editKey) this._svc("edit_contact",{number:this._editKey,name,tag:this._tag,new_number:number});
    else this._svc("add_contact",{number,name,tag:this._tag});
    this._formOpen = false;
    $("#form").classList.remove("show");
    this._render();
  }

  _initials(n){const p=(n||"?").trim().split(/\s+/);return ((p[0]||"")[0]||"?").toUpperCase()+(p[1]?(p[1][0]||"").toUpperCase():"");}
  _esc(s){return (s||"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[m]));}
}

customElements.define("livebox-callmon-card", LiveboxCallmonCard);
window.customCards = window.customCards || [];
window.customCards.push({
  type: "livebox-callmon-card",
  name: "Livebox Call Monitor Card",
  description: "Call log + contacts CRUD for the Livebox Call Monitor integration",
});
console.info("%c LIVEBOX-CALLMON-CARD %c loaded ", "background:#2ea3ff;color:#fff", "");
