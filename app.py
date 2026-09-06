from __future__ import annotations

import base64
import html
from io import BytesIO
from pathlib import Path
from typing import Optional

import streamlit as st
from dotenv import load_dotenv
from PIL import Image, UnidentifiedImageError

from behavior_memory import (
    BehaviorAnalysis,
    analyze_behavior,
    build_memory_entry,
    demo_grooming_analysis,
)
from pet_director import CompanionResponse, get_companion_response


load_dotenv()

st.set_page_config(
    page_title="Beside",
    layout="centered",
    initial_sidebar_state="collapsed",
)


TRAITS = ["黏人", "高冷", "爱踩奶", "贪睡", "胆小", "话痨", "爱撒娇", "爱捣乱"]
COMPANION_BEHAVIORS = [
    "靠着我",
    "趴在我附近",
    "给我踩奶",
    "主动蹭我",
    "看我一眼然后走开",
]
EMOTION_QUESTIONS = [
    ("happy", "当你很开心时，它通常会怎么回应？"),
    ("sad", "当你难过时，它通常会怎么回应？"),
    ("anxious", "当你焦虑或烦躁时，它通常会怎么回应？"),
    ("tired", "当你很累或低落时，它通常会怎么回应？"),
]
PROFILE_ACTIONS = ["come_closer", "knead", "curl_up", "grooming"]
PROFILE_ACTION_LABELS = {
    "come_closer": "靠近",
    "knead": "轻轻踩奶",
    "curl_up": "安静陪着",
    "grooming": "认真理毛",
}


GLOBAL_CSS = """
<style>
:root {
  /* Final visual system hooks. Values are centralized here for the approved reskin. */
  --bg: #F8F8F4;
  --text-primary: #263A33;
  --sage: #789986;
  --muted-pink: #D9A7AD;
  --powder-blue-green: #9FC7C9;
  --page-padding: .9rem;
  --radius-image: 28px;
  --radius-input: 999px;
  --nav-height: 2rem;
  --shared-room-background-opacity: 0;
  --cream: #f2ede1;
  --cream-muted: #b8b2a5;
  --apricot: #d7a36b;
  --deep-green: #17201a;
  --olive: #47503a;
  --olive-dark: #30372a;
  --line: rgba(244, 237, 219, .11);
}

html, body, [class*="css"] {
  font-family: "PingFang SC", "Microsoft YaHei", sans-serif;
}
header, footer, #MainMenu, [data-testid="stToolbar"], [data-testid="stDecoration"] {
  display: none !important;
}
[data-testid="stAppViewContainer"] {
  background:
    radial-gradient(circle at 78% 8%, rgba(209, 166, 111, .11), transparent 25rem),
    radial-gradient(circle at 12% 85%, rgba(72, 88, 66, .2), transparent 28rem),
    linear-gradient(155deg, #172019 0%, #1d241d 52%, #141914 100%);
  color: var(--cream);
}
[data-testid="stAppViewContainer"]::before {
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  opacity: .12;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 180 180' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.75' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.15'/%3E%3C/svg%3E");
}
[data-testid="stMainBlockContainer"] {
  max-width: 570px;
  padding: 1.25rem .9rem 5.5rem;
  position: relative;
  z-index: 1;
}
[data-testid="stVerticalBlock"] { gap: .72rem; }

.create-kicker {
  color: rgba(215, 163, 107, .64);
  font-size: .61rem;
  letter-spacing: .16em;
  margin-bottom: .35rem;
}
.create-title {
  color: var(--cream);
  font-family: "Songti SC", "STSong", serif;
  font-size: clamp(1.65rem, 7vw, 2.15rem);
  font-weight: 600;
  line-height: 1.16;
  margin: 0;
}
.create-copy {
  color: rgba(214, 208, 195, .58);
  font-size: .79rem;
  margin: .42rem 0 .25rem;
}
.required-note {
  color: rgba(205, 199, 187, .46);
  font-size: .67rem;
  margin-top: -.45rem;
}

[data-testid="stWidgetLabel"] p, label { color: rgba(239, 232, 216, .79) !important; font-size: .79rem !important; }
[data-testid="stFileUploader"] {
  background: rgba(31, 40, 32, .65);
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: .15rem;
}
[data-testid="stFileUploaderDropzone"] {
  min-height: 62px;
  padding: .55rem .75rem;
  background: transparent;
  border: 0;
}
[data-testid="stFileUploaderDropzoneInstructions"] span { color: rgba(232, 225, 211, .75); font-size: .78rem; }
[data-testid="stFileUploaderDropzoneInstructions"] small { color: rgba(202, 197, 186, .42); font-size: .62rem; }

.st-key-upload_preview {
  overflow: hidden;
  border: 1px solid rgba(242, 232, 210, .13);
  border-radius: 22px;
  background: #20271f;
  box-shadow: 0 18px 44px rgba(4, 9, 5, .22);
}
.st-key-upload_preview > [data-testid="stElementContainer"],
.st-key-upload_preview [data-testid="stFullScreenFrame"],
.st-key-upload_preview [data-testid="stFullScreenFrame"] > div,
.st-key-upload_preview [data-testid="stImage"] {
  width: 100% !important;
}
.st-key-upload_preview [data-testid="stImageContainer"] {
  width: 100% !important;
  margin: 0;
}
.st-key-upload_preview [data-testid="stImageContainer"] img {
  width: 100% !important;
  height: 212px !important;
  object-fit: cover;
  display: block;
}

[data-testid="stTextInputRootElement"], [data-baseweb="select"] > div {
  min-height: 42px;
  background: rgba(239, 235, 222, .055) !important;
  border: 1px solid var(--line) !important;
  border-radius: 13px !important;
}
[data-testid="stTextInputRootElement"] input { color: var(--cream) !important; }
[data-baseweb="tag"] { background: rgba(106, 119, 86, .42) !important; }
[data-testid="stRadio"] > div { gap: .3rem .75rem; }
[data-testid="stRadio"] label { margin-right: 0; }

.stButton > button[kind="primary"] {
  width: 100%;
  min-height: 2.7rem;
  border: 0;
  border-radius: 14px;
  background: linear-gradient(135deg, #dcb17d, #c9935e);
  color: #211b14;
  font-size: .9rem;
  font-weight: 600;
  box-shadow: 0 10px 26px rgba(176, 119, 64, .13);
}
.stButton > button[kind="primary"]:hover {
  color: #18130f;
  border: 0;
  background: linear-gradient(135deg, #e4bb88, #d09b67);
}
.stButton > button[kind="tertiary"] {
  min-height: 1.5rem;
  width: auto;
  padding: 0;
  margin-left: auto;
  color: rgba(206, 199, 184, .47);
  background: transparent;
  border: 0;
  box-shadow: none;
  font-size: .68rem;
}
.stButton > button[kind="tertiary"]:hover {
  color: rgba(235, 226, 208, .8);
  background: transparent;
  border: 0;
}
.validation { color: #dfac98; font-size: .78rem; margin: .3rem 0; }

.st-key-room_top {
  min-height: 42px;
  position: relative;
}
.st-key-room_top [data-testid="stVerticalBlock"] { gap: 0; }
.st-key-room_top > [data-testid="stElementContainer"]:last-child {
  position: absolute;
  right: 0;
  top: .15rem;
  width: max-content !important;
}
.st-key-room_top [data-testid="stButton"] {
  width: max-content;
}
.st-key-room_top [data-testid="stButton"] button {
  min-width: max-content;
  white-space: nowrap;
}
.room-name {
  color: rgba(244, 237, 223, .88);
  font-family: "Songti SC", "STSong", serif;
  font-size: 1rem;
  line-height: 1.2;
}
.room-sub {
  color: rgba(197, 191, 178, .42);
  font-size: .62rem;
  letter-spacing: .06em;
  margin-top: .14rem;
}

.room-shell {
  position: relative;
  height: min(65vh, 620px);
  min-height: 455px;
  overflow: hidden;
  border: 1px solid rgba(238, 229, 208, .085);
  border-radius: 28px;
  background:
    radial-gradient(circle at 76% 20%, rgba(225, 172, 109, .18), transparent 12rem),
    linear-gradient(180deg, #222c24 0%, #1d271f 50%, #182019 100%);
  box-shadow: 0 30px 80px rgba(2, 8, 4, .29);
}
.room-media-layer,
.legacy-room-fallback {
  position: absolute;
  inset: 0;
}
.room-media-layer {
  z-index: 0;
}
.room-media-frame {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
  border: 0;
}
.legacy-room-fallback {
  z-index: 1;
}
.room-shell.has-fallback .room-media-layer {
  display: none;
}
.room-shell::before {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, transparent 58%, rgba(7, 12, 8, .25));
  pointer-events: none;
}
.lamp {
  position: absolute;
  z-index: 1;
  right: 8%;
  top: 8%;
  width: 38px;
  height: 68px;
  opacity: .76;
}
.lamp::before {
  content: "";
  position: absolute;
  width: 38px;
  height: 27px;
  border-radius: 50% 50% 16% 16%;
  background: #c7945f;
  box-shadow: 0 0 60px rgba(221, 164, 99, .28);
}
.lamp::after {
  content: "";
  position: absolute;
  top: 25px;
  left: 17px;
  width: 3px;
  height: 42px;
  border-radius: 4px;
  background: rgba(148, 126, 92, .72);
}
.ambient-glow {
  position: absolute;
  z-index: 0;
  left: 6%;
  top: 11%;
  width: 42%;
  height: 30%;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(121, 140, 111, .08), transparent 70%);
}

.sofa-back {
  position: absolute;
  z-index: 1;
  left: 6%;
  right: 6%;
  bottom: 7%;
  height: 67%;
  border-radius: 46% 46% 28% 28% / 38% 38% 25% 25%;
  background:
    radial-gradient(ellipse at 50% 20%, rgba(135, 145, 105, .16), transparent 42%),
    linear-gradient(145deg, #566047 0%, #414a38 48%, #343c2f 100%);
  box-shadow:
    0 25px 36px rgba(2, 7, 3, .36),
    inset 0 2px 2px rgba(240, 233, 203, .08),
    inset 0 -20px 42px rgba(18, 24, 17, .24);
}
.sofa-back::after {
  content: "";
  position: absolute;
  left: 16%;
  right: 16%;
  top: 13%;
  height: 58%;
  border-radius: 50%;
  box-shadow: inset 0 10px 24px rgba(21, 28, 19, .2);
  border-top: 1px solid rgba(241, 233, 205, .045);
}
.sofa-seat {
  position: absolute;
  z-index: 2;
  left: 12%;
  right: 12%;
  bottom: 5%;
  height: 25%;
  border-radius: 50%;
  background: linear-gradient(180deg, #4a543e, #353d30);
  box-shadow: 0 18px 26px rgba(4, 9, 5, .3), inset 0 4px 9px rgba(238, 229, 201, .045);
  transform-origin: center;
}
.sofa-arm {
  position: absolute;
  z-index: 4;
  bottom: 10%;
  width: 28%;
  height: 36%;
  border-radius: 52% 48% 42% 42%;
  background: linear-gradient(145deg, #4c563f, #374031);
  box-shadow: inset 0 2px 5px rgba(239, 231, 205, .04);
}
.sofa-arm.left { left: 5%; transform: rotate(6deg); }
.sofa-arm.right { right: 5%; transform: rotate(-6deg); }

.pet-wrap {
  position: absolute;
  z-index: 3;
  left: 50%;
  bottom: 15%;
  width: min(72%, 370px);
  height: 64%;
  transform: translateX(-50%);
  transform-origin: 50% 88%;
  filter: drop-shadow(0 22px 18px rgba(3, 7, 4, .28));
}
.pet-image {
  width: 100%;
  height: 100%;
  object-fit: cover !important;
  object-position: center !important;
  display: block;
  border-radius: 26px 26px 38% 38% / 26px 26px 18% 18%;
  border: 1px solid rgba(245, 237, 215, .11);
  -webkit-mask-image: linear-gradient(to bottom, #000 0%, #000 82%, transparent 100%);
  mask-image: linear-gradient(to bottom, #000 0%, #000 82%, transparent 100%);
  animation: breathe 5.8s ease-in-out infinite;
}
.pet-wrap.listening .pet-image { animation: listen 1.3s ease-in-out infinite alternate; }
.pet-wrap.action-come_closer { animation: comeCloser 4.4s cubic-bezier(.2,.75,.2,1) forwards; }
.pet-wrap.action-come_closer .pet-image { animation: breathe 3.2s ease-in-out infinite, nuzzle 1.1s ease-in-out 1.25s 2; }
.pet-wrap.action-knead { animation: kneadBody 3.8s ease-in-out forwards; }
.pet-wrap.action-knead ~ .sofa-seat { animation: seatKnead .58s ease-in-out .6s 6 alternate; }
.pet-wrap.action-knead ~ .sofa-arm.left { animation: armLeftKnead 1.16s ease-in-out .6s 3; }
.pet-wrap.action-knead ~ .sofa-arm.right { animation: armRightKnead 1.16s ease-in-out 1.18s 3; }
.pet-wrap.action-curl_up { animation: curlUp 4.3s cubic-bezier(.22,.72,.18,1) forwards; }
.pet-wrap.action-curl_up .pet-image { animation: quietBreathe 7s ease-in-out 2.6s infinite; }
.pet-wrap.action-grooming { animation: groomingBody 3.8s ease-in-out forwards; }
.pet-wrap.action-grooming .pet-image { animation: groomingImage 1.25s ease-in-out .55s 2 alternate; }

.pressure-marks {
  position: absolute;
  z-index: 5;
  left: 50%;
  bottom: 13%;
  width: 124px;
  height: 34px;
  transform: translateX(-50%);
  pointer-events: none;
}
.pressure-marks span {
  position: absolute;
  width: 42px;
  height: 9px;
  border-radius: 50%;
  border-bottom: 2px solid rgba(213, 214, 176, .15);
  opacity: 0;
}
.action-knead ~ .pressure-marks span:first-child { left: 5px; animation: pressure .58s .6s 3 alternate; }
.action-knead ~ .pressure-marks span:last-child { right: 5px; animation: pressure .58s .89s 3 alternate; }

.listen-copy {
  position: absolute;
  z-index: 7;
  left: 0;
  right: 0;
  bottom: 3.3%;
  color: rgba(213, 207, 192, .48);
  font-size: .68rem;
  letter-spacing: .14em;
  text-align: center;
  animation: softPulse 1.5s ease-in-out infinite;
}
.caption {
  position: absolute;
  z-index: 7;
  left: 7%;
  right: 7%;
  bottom: 3.2%;
  color: rgba(247, 240, 225, .94);
  font-family: "Songti SC", "STSong", serif;
  font-size: clamp(.9rem, 3.8vw, 1.08rem);
  line-height: 1.6;
  text-align: center;
  text-shadow: 0 2px 18px rgba(0, 0, 0, .82);
  opacity: 0;
  animation: captionLife 5.7s ease 1.7s both;
}
.motion-video {
  position: absolute;
  z-index: 6;
  inset: 0;
  width: 100%;
  height: 100%;
  display: block;
  object-fit: cover;
  object-position: center;
  border: 0;
  background: transparent;
  opacity: 0;
  animation: motionVideoLife 5.25s ease forwards;
}
.room-shell.has-motion .caption {
  animation: motionCaptionLife 5s ease 1.55s both;
}

@keyframes breathe { 0%,100%{transform:scale(1)} 50%{transform:scale(1.012) translateY(-2px)} }
@keyframes quietBreathe { 0%,100%{transform:scale(1)} 50%{transform:scale(1.006)} }
@keyframes listen { from{transform:scale(1)} to{transform:scale(1.014) translateY(-3px)} }
@keyframes softPulse { 0%,100%{opacity:.32} 50%{opacity:.72} }
@keyframes comeCloser { 0%{transform:translateX(-50%) scale(1)} 52%{transform:translateX(-50%) translateY(-5px) scale(1.075)} 100%{transform:translateX(-48%) translateY(-4px) scale(1.07)} }
@keyframes nuzzle { 0%,100%{translate:0 0} 50%{translate:7px 1px} }
@keyframes kneadBody { 0%{transform:translateX(-50%)} 22%{transform:translateX(-51%) translateY(3px) scaleY(.99)} 38%{transform:translateX(-49%) translateY(0)} 54%{transform:translateX(-51%) translateY(3px) scaleY(.99)} 70%{transform:translateX(-49%) translateY(0)} 86%,100%{transform:translateX(-50%) translateY(2px)} }
@keyframes seatKnead { from{transform:scaleX(1) scaleY(1)} to{transform:scaleX(1.015) scaleY(.95)} }
@keyframes armLeftKnead { 0%,100%{transform:rotate(6deg)} 50%{transform:rotate(6deg) translateY(4px)} }
@keyframes armRightKnead { 0%,100%{transform:rotate(-6deg)} 50%{transform:rotate(-6deg) translateY(4px)} }
@keyframes pressure { from{opacity:0;transform:scaleX(.75)} to{opacity:.8;transform:scaleX(1)} }
@keyframes curlUp { 0%{transform:translateX(-50%) scale(1)} 65%,100%{transform:translateX(-50%) translateY(34px) scale(.89)} }
@keyframes groomingBody { 0%,100%{transform:translateX(-50%)} 45%{transform:translateX(-50%) translateY(5px) scale(.98)} }
@keyframes groomingImage { from{transform:rotate(0)} to{transform:rotate(-1.3deg) translateY(3px)} }
@keyframes captionLife { 0%{opacity:0;transform:translateY(7px)} 13%,72%{opacity:1;transform:translateY(0)} 100%{opacity:0;transform:translateY(-3px)} }
@keyframes motionVideoLife {
  0% { opacity: 0; visibility: visible; }
  4%, 94% { opacity: 1; visibility: visible; }
  100% { opacity: 0; visibility: hidden; }
}
@keyframes motionCaptionLife {
  0% { opacity: 0; transform: translateY(7px); }
  4%, 72% { opacity: 1; transform: translateY(0); }
  100% { opacity: 0; transform: translateY(-3px); }
}

.profile-intro, .memory-count {
  color: rgba(205, 199, 187, .48);
  font-size: .68rem;
}
.analysis-card {
  padding: .8rem .85rem;
  border: 1px solid rgba(242, 232, 210, .1);
  border-radius: 14px;
  background: rgba(239, 235, 222, .035);
  color: rgba(235, 229, 216, .72);
  font-size: .75rem;
  line-height: 1.65;
}
.analysis-card strong { color: rgba(244, 237, 223, .9); font-weight: 500; }
.st-key-main_nav {
  margin: -.1rem 0 .3rem;
  padding: .24rem;
  border: 1px solid rgba(242, 232, 210, .08);
  border-radius: 14px;
  background: rgba(239, 235, 222, .035);
}
.st-key-main_nav [data-testid="stHorizontalBlock"] {
  gap: .25rem;
}
.st-key-main_nav [data-testid="stColumn"] {
  min-width: 0;
}
.st-key-main_nav [data-testid="stButton"] button {
  width: 100%;
  min-height: 2rem;
  margin: 0;
  padding: .2rem .35rem;
  border: 0;
  border-radius: 10px;
  background: transparent;
  color: rgba(222, 215, 199, .48);
  font-size: .72rem;
  box-shadow: none;
}
.st-key-main_nav [data-testid="stButton"] button[kind="primary"] {
  background: rgba(238, 229, 207, .09);
  color: rgba(246, 238, 220, .9);
}
.shared-room-background {
  position: fixed;
  z-index: 0;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
  opacity: var(--shared-room-background-opacity);
}
.shared-room-background img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.record-header {
  padding: .2rem .1rem .35rem;
}
.record-title {
  color: var(--cream);
  font-family: "Songti SC", "STSong", serif;
  font-size: clamp(1.45rem, 6.5vw, 1.9rem);
  font-weight: 600;
  line-height: 1.2;
  margin: 0;
}
.record-subtitle {
  color: rgba(205, 199, 187, .48);
  font-size: .7rem;
  margin: .38rem 0 0;
}
.record-saved {
  padding: 1rem;
  border: 1px solid rgba(242, 232, 210, .1);
  border-radius: 16px;
  background: rgba(239, 235, 222, .04);
  color: rgba(244, 237, 223, .9);
  font-family: "Songti SC", "STSong", serif;
  text-align: center;
}
.st-key-response_explanation,
.st-key-response_explanation_live {
  opacity: 0;
  animation: explanationAppear .35s ease 1.7s forwards;
}
@keyframes explanationAppear { to { opacity: 1; } }

.sticker-header {
  padding: .25rem .15rem .45rem;
}
.sticker-title {
  color: var(--cream);
  font-family: "Songti SC", "STSong", serif;
  font-size: clamp(1.55rem, 7vw, 2rem);
  font-weight: 600;
  line-height: 1.2;
  margin: 0;
}
.sticker-subtitle {
  color: rgba(205, 199, 187, .48);
  font-size: .72rem;
  margin: .38rem 0 0;
}
.sticker-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: .72rem;
  width: 100%;
  padding: .15rem 0 .5rem;
}
.sticker-card {
  min-width: 0;
  overflow: hidden;
  padding: .42rem .42rem .7rem;
  border: 1px solid rgba(246, 235, 210, .42);
  border-radius: 18px;
  background: linear-gradient(155deg, #eee5d3, #ddd2bb);
  box-shadow: 0 12px 28px rgba(4, 8, 5, .2);
  color: #2d3429;
}
.sticker-card:nth-child(odd) { transform: rotate(-.6deg); }
.sticker-card:nth-child(even) { transform: rotate(.65deg); }
.sticker-image,
.sticker-placeholder {
  display: block;
  width: 100%;
  aspect-ratio: 1;
  object-fit: cover;
  border: 3px solid rgba(255, 251, 239, .82);
  border-radius: 14px;
  box-sizing: border-box;
  background:
    radial-gradient(circle at 68% 28%, rgba(221, 174, 112, .28), transparent 34%),
    linear-gradient(145deg, #697158, #3c4737);
}
.sticker-placeholder {
  position: relative;
}
.sticker-placeholder::after {
  content: "";
  position: absolute;
  inset: 24%;
  border-radius: 48% 52% 44% 56%;
  background: rgba(239, 226, 196, .12);
  box-shadow: 0 0 24px rgba(240, 211, 162, .08);
}
.sticker-behavior {
  margin: .58rem .18rem 0;
  color: #273126;
  font-family: "Songti SC", "STSong", serif;
  font-size: .92rem;
  font-weight: 600;
  line-height: 1.25;
}
.sticker-context {
  margin: .25rem .18rem 0;
  color: rgba(49, 57, 45, .58);
  font-size: .64rem;
  line-height: 1.35;
}
.sticker-description {
  margin: .38rem .18rem 0;
  color: rgba(40, 48, 37, .82);
  font-size: .7rem;
  line-height: 1.55;
}
.st-key-sticker_back {
  margin-top: .15rem;
}
.st-key-sticker_back [data-testid="stButton"] button {
  margin: 0 auto;
}

.input-note {
  color: rgba(190, 185, 173, .32);
  font-size: .61rem;
  text-align: center;
  margin: .1rem 0 -.25rem;
}
[data-testid="stBottomBlockContainer"] {
  background: linear-gradient(180deg, transparent, rgba(20, 27, 21, .96) 25%);
}
[data-testid="stChatInput"] {
  border: 1px solid rgba(240, 231, 211, .1);
  border-radius: 999px;
  background: rgba(237, 232, 217, .06);
  box-shadow: 0 10px 30px rgba(3, 8, 4, .22);
}
[data-testid="stChatInput"] textarea {
  color: var(--cream);
  font-size: .82rem;
}
[data-testid="stChatInputSubmitButton"] {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  color: #2a241b;
  background: #cf9a63;
}

@media (max-width: 640px) {
  [data-testid="stMainBlockContainer"] { padding: .85rem .68rem 5.2rem; }
  [data-testid="stVerticalBlock"] { gap: .55rem; }
  .st-key-upload_preview [data-testid="stImageContainer"] img { height: 190px !important; }
  .sticker-grid { gap: .58rem; }
  .sticker-card { padding: .36rem .36rem .62rem; border-radius: 16px; }
  .sticker-image, .sticker-placeholder { border-radius: 12px; }
  .room-shell { height: 66vh; min-height: 470px; border-radius: 24px; }
  .pet-wrap { width: 76%; height: 62%; bottom: 16%; }
  .sofa-back { left: 4%; right: 4%; height: 65%; }
  .sofa-seat { left: 9%; right: 9%; }
  .sofa-arm { width: 29%; }
}
@media (prefers-reduced-motion: reduce) {
  .pet-wrap, .pet-image, .sofa-seat, .sofa-arm, .pressure-marks span, .caption, .listen-copy {
    animation-duration: .01ms !important;
    animation-iteration-count: 1 !important;
  }
  .room-shell.has-motion .caption {
    animation: motionCaptionLife 5s ease 1.55s both !important;
  }
}
</style>
"""


FINAL_APPROVED_CSS = """
<style>
:root {
  --bg: #F8F8F4;
  --canvas-subtle: #F3F4EF;
  --surface: #FFFEFA;
  --text-primary: #24352F;
  --text-secondary: #68756F;
  --sage: #9CAF99;
  --sage-soft: #E7EDE3;
  --dusty-pink: #EAD9DB;
  --soft-blue: #DCE8EC;
  --muted-coral: #D98F7D;
  --border: #DFE4DD;
  --cta: #24352F;
  --cta-text: #F9FAF6;
  --page-padding: 20px;
  --radius-image: 22px;
  --radius-input: 14px;
  --nav-height: 60px;
}

html, body, [class*="css"] {
  font-family: Inter, -apple-system, BlinkMacSystemFont, "SF Pro Text", "PingFang SC", sans-serif;
}
html, body {
  background: var(--bg);
}
[data-testid="stAppViewContainer"] {
  background: var(--bg);
  color: var(--text-primary);
}
[data-testid="stAppViewContainer"]::before {
  display: none;
}
[data-testid="stMainBlockContainer"] {
  max-width: 430px;
  padding: 24px var(--page-padding) 148px;
}
[data-testid="stVerticalBlock"] {
  gap: 10px;
}
p, li, span, div {
  text-rendering: optimizeLegibility;
}
[data-testid="stWidgetLabel"] p,
label {
  color: var(--text-primary) !important;
  font-size: 13px !important;
  font-weight: 500 !important;
}

.brand-word {
  color: var(--sage);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: .14em;
  margin-bottom: 11px;
  text-transform: uppercase;
}
.create-title,
.record-title,
.sticker-title {
  color: var(--text-primary);
  font-family: inherit;
  font-size: 28px;
  font-weight: 500;
  letter-spacing: -.025em;
  line-height: 32px;
  margin: 0;
  white-space: nowrap;
}
.create-title::after,
.record-title::after,
.sticker-title::after {
  content: "";
  display: block;
  width: 58px;
  height: 4px;
  margin-top: 7px;
  border-radius: 99px;
  background: linear-gradient(175deg, rgba(156,175,153,.72), rgba(156,175,153,.26));
  transform: rotate(-1.4deg);
}
.create-copy,
.record-subtitle,
.sticker-subtitle {
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 19px;
  margin: 5px 0 0;
}
.create-copy {
  min-height: 20px;
  padding-bottom: 8px;
  line-height: 20px;
}

.shared-room-background {
  opacity: 1;
  background: var(--bg);
}
.shared-room-background::after {
  content: "";
  position: absolute;
  inset: 0;
  background: rgba(248, 248, 244, .36);
}
.shared-room-background img {
  opacity: .63;
  filter: brightness(1.05) saturate(.72) contrast(.78) blur(.45px);
  object-fit: cover;
  object-position: center;
}
.shared-room-background--create::after {
  background: rgba(248, 248, 244, .68);
}
.shared-room-background--create img {
  opacity: .28;
  filter: none;
}

.st-key-create_form {
  padding: 0 0 6px;
}
.st-key-create_form > [data-testid="stVerticalBlock"] {
  gap: 10px;
}
.st-key-create_form [data-testid="stFileUploader"] {
  padding: 0;
  border: 1px dashed rgba(36,53,47,.18);
  border-radius: 18px;
  background: rgba(255,254,250,.70);
}
.st-key-create_form [data-testid="stFileUploaderDropzone"] {
  min-height: 72px;
  padding: 10px 12px;
  border: 0;
  background: transparent;
}
.st-key-create_form [data-testid="stFileUploaderDropzoneInstructions"] {
  display: none;
}
.st-key-create_form [data-testid="stFileUploaderDropzone"]::before {
  content: "清晰、自然的生活照就很好";
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 17px;
}
.st-key-create_form [data-testid="stFileUploaderDropzone"] button {
  min-height: 36px;
  padding: 0 12px;
  border: 1px solid #B8C5B5;
  border-radius: 12px;
  background: var(--sage-soft);
  color: transparent;
  font-size: 0;
  box-shadow: none;
}
.st-key-create_form [data-testid="stFileUploaderDropzone"] button::after {
  content: "选择照片";
  color: var(--text-primary);
  font-size: 12px;
}
.st-key-create_form:has(.st-key-upload_preview img) [data-testid="stFileUploader"] {
  width: max-content;
  margin-left: auto;
  border: 0;
  background: transparent;
}
.st-key-create_form:has(.st-key-upload_preview img) [data-testid="stFileUploaderDropzone"] {
  min-height: 32px;
  padding: 0;
}
.st-key-create_form:has(.st-key-upload_preview img) [data-testid="stFileUploaderDropzone"]::before {
  display: none;
}
.st-key-create_form:has(.st-key-upload_preview img) [data-testid="stFileUploaderDropzone"] button::after {
  content: "更换照片";
}
.st-key-create_form:has(.st-key-upload_preview img) [data-testid="stFileUploader"] [data-testid="stWidgetLabel"],
.st-key-create_form [data-testid="stFileUploaderFile"],
.st-key-create_form [data-testid="stFileUploaderFileName"],
.st-key-create_form [data-testid="stFileUploaderFileData"] {
  display: none !important;
}
.st-key-upload_preview {
  overflow: hidden;
  border: 0;
  border-radius: 20px;
  background: transparent;
  box-shadow: none;
}
.st-key-upload_preview [data-testid="stImageContainer"] img {
  width: 100% !important;
  height: 238px !important;
  border-radius: 20px;
  object-fit: cover;
}
.st-key-create_form [data-testid="stHorizontalBlock"] {
  gap: 10px;
}
.st-key-identity_row [data-testid="stHorizontalBlock"],
.st-key-behavior_observation_row [data-testid="stHorizontalBlock"],
[class*="st-key-profile_row_"] [data-testid="stHorizontalBlock"] {
  flex-direction: row !important;
  flex-wrap: nowrap !important;
}
.st-key-identity_row [data-testid="stColumn"],
.st-key-behavior_observation_row [data-testid="stColumn"],
[class*="st-key-profile_row_"] [data-testid="stColumn"] {
  min-width: 0 !important;
  width: auto !important;
}
.st-key-identity_row [data-testid="stColumn"]:first-child {
  flex: .68 1 0 !important;
}
.st-key-identity_row [data-testid="stColumn"]:last-child {
  flex: 1.32 1 0 !important;
}
.required-note {
  color: var(--text-secondary);
  font-size: 11px;
  line-height: 15px;
  margin: -7px 0 2px;
}

[data-testid="stTextInputRootElement"],
[data-baseweb="select"] > div {
  min-height: 42px;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-input) !important;
  background: rgba(255,254,250,.95) !important;
  box-shadow: none !important;
}
[data-testid="stTextInputRootElement"]:focus-within,
[data-baseweb="select"] > div:focus-within {
  border-color: var(--sage) !important;
  box-shadow: 0 0 0 3px rgba(156,175,153,.16) !important;
}
[data-testid="stTextInputRootElement"] input,
[data-baseweb="select"] input,
[data-baseweb="select"] div {
  color: var(--text-primary) !important;
  font-size: 16px !important;
}
[data-baseweb="base-input"] {
  background: transparent !important;
}
[data-baseweb="tag"] {
  min-height: 25px;
  border-radius: 999px !important;
  background: var(--sage-soft) !important;
  color: var(--text-primary) !important;
  font-size: 12px !important;
}

.st-key-create_form [data-testid="stRadio"] > label {
  margin-bottom: 5px;
}
.st-key-create_form [data-testid="stRadio"] [role="radiogroup"] {
  display: flex;
  flex-flow: row wrap;
  gap: 6px;
}
.st-key-create_form [data-testid="stRadio"] [role="radiogroup"] label {
  min-height: 30px;
  margin: 0;
  padding: 5px 9px;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: rgba(255,254,250,.86);
}
.st-key-create_form [data-testid="stRadio"] [role="radiogroup"] label:has(input:checked) {
  border-color: #BECBB9;
  background: var(--sage-soft);
}
.st-key-create_form [data-testid="stRadio"] [role="radiogroup"] label > div:first-child {
  display: none;
}
.st-key-create_form [data-testid="stRadio"] [role="radiogroup"] p {
  color: var(--text-primary);
  font-size: 12px;
}
.profile-heading {
  margin-top: 4px;
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 500;
  line-height: 20px;
}
[class*="st-key-profile_row_"] {
  min-height: 42px;
  padding: 3px 0;
  border-bottom: 1px solid rgba(36,53,47,.08);
}
[class*="st-key-profile_row_"] > [data-testid="stVerticalBlock"] {
  gap: 0;
}
[class*="st-key-profile_row_"] [data-testid="stHorizontalBlock"] {
  align-items: center;
  gap: 7px;
}
[class*="st-key-profile_row_"] [data-testid="stColumn"]:nth-child(1) {
  flex: 0 0 4px !important;
}
[class*="st-key-profile_row_"] [data-testid="stColumn"]:nth-child(2) {
  flex: 0 0 104px !important;
}
[class*="st-key-profile_row_"] [data-testid="stColumn"]:nth-child(3) {
  flex: 1 1 auto !important;
}
[class*="st-key-profile_row_"] [data-testid="stColumn"]:nth-child(4) {
  flex: 0 0 10px !important;
}
.profile-accent {
  display: block;
  width: 3px;
  height: 24px;
  border-radius: 999px;
  background: var(--sage);
}
.st-key-profile_row_sad .profile-accent { background: var(--powder-blue-green); }
.st-key-profile_row_anxious .profile-accent { background: var(--muted-pink); }
.st-key-profile_row_tired .profile-accent { background: #C9D5C5; }
.profile-label {
  display: block;
  color: var(--text-primary);
  font-size: 13px;
  line-height: 18px;
  white-space: nowrap;
}
.profile-arrow {
  display: block;
  color: #95A19B;
  font-size: 20px;
  line-height: 42px;
  text-align: right;
}
[class*="st-key-profile_row_"] [data-baseweb="select"] > div {
  min-height: 34px;
  border: 0 !important;
  background: transparent !important;
}
[class*="st-key-profile_row_"] [data-baseweb="select"] div {
  font-size: 13px !important;
  text-align: right;
}

.stButton > button[kind="primary"] {
  width: 100%;
  min-height: 48px;
  border: 0;
  border-radius: 15px;
  background: var(--cta);
  color: var(--cta-text);
  font-size: 14px;
  font-weight: 500;
  box-shadow: none;
}
.stButton > button[kind="primary"]:hover {
  border: 0;
  background: #30463E;
  color: var(--cta-text);
}
.stButton > button[kind="primary"]:disabled {
  background: #CFD8CD;
  color: rgba(36,53,47,.48);
}
.stButton > button[kind="tertiary"] {
  color: var(--text-secondary);
  font-size: 12px;
}

.st-key-main_nav {
  position: fixed;
  z-index: 2000;
  left: 50%;
  bottom: max(10px, env(safe-area-inset-bottom));
  width: min(calc(100vw - 24px), 406px);
  height: var(--nav-height);
  margin: 0;
  padding: 5px;
  border: 0;
  border-top: 1px solid rgba(36,53,47,.07);
  border-radius: 20px;
  background: rgba(255,254,250,.90);
  box-shadow: 0 4px 18px rgba(40,55,47,.09);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  transform: translateX(-50%);
}
.st-key-main_nav > [data-testid="stVerticalBlock"],
.st-key-main_nav [data-testid="stHorizontalBlock"] {
  height: 100%;
  gap: 4px;
}
.st-key-main_nav [data-testid="stButton"] button {
  min-height: 50px;
  padding: 0 8px;
  border: 0;
  border-radius: 15px;
  background: transparent;
  color: #84908A;
  font-size: 11px;
  font-weight: 500;
  box-shadow: none;
}
.st-key-main_nav [data-testid="stButton"] button[kind="primary"] {
  background: var(--sage-soft);
  color: var(--text-primary);
}

.st-key-room_top {
  position: fixed;
  z-index: 3;
  top: 8px;
  left: 50%;
  width: min(calc(100vw - 40px), 390px);
  min-height: 72px;
  margin: 0;
  transform: translateX(-50%);
}
.room-name {
  color: var(--text-primary);
  font-family: inherit;
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -.025em;
  line-height: 32px;
  text-shadow: 0 1px 10px rgba(255,254,250,.72);
}
.room-sub {
  color: var(--text-secondary);
  font-size: 14px;
  letter-spacing: 0;
  line-height: 15px;
  margin-top: 2px;
  text-shadow: 0 1px 8px rgba(255,254,250,.78);
}
.room-sub::before {
  content: "";
  display: inline-block;
  width: 6px;
  height: 6px;
  margin-right: 6px;
  border-radius: 50%;
  background: var(--sage);
  vertical-align: 1px;
}
.st-key-room_top [data-testid="stButton"] button {
  color: #8A9690;
  font-size: 18px;
  letter-spacing: .12em;
}
.room-shell {
  position: fixed;
  z-index: 1;
  top: 86px;
  left: 50%;
  width: min(calc(100vw - 40px), 390px);
  height: 552px !important;
  min-height: 552px;
  overflow: visible;
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
  transform: translateX(-50%);
}
[data-testid="stElementContainer"]:has(.room-shell) {
  height: 552px;
  min-height: 552px;
}
.room-shell::before {
  display: none;
}
.room-media-layer {
  position: absolute !important;
  inset: 0 0 auto !important;
  width: 100%;
  height: 500px;
  overflow: hidden;
  border-radius: 22px;
  background: var(--bg);
  transform: none;
}
.room-media-frame {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  border-radius: 22px;
  object-fit: cover;
  object-position: center;
}
.legacy-room-fallback,
.lamp,
.ambient-glow,
.sofa-back,
.sofa-seat,
.sofa-arm,
.pressure-marks,
.pet-wrap {
  display: none !important;
}
.room-shell.has-fallback .room-media-layer {
  display: block;
}
.room-idle-media.fallback-action-come_closer {
  animation: besideComeCloser 4.4s cubic-bezier(.2,.75,.2,1) forwards;
}
.room-idle-media.fallback-action-curl_up {
  animation: besideCurlUp 4.4s ease forwards;
}
@keyframes besideComeCloser {
  from { transform: scale(1); }
  to { transform: scale(1.035) translateY(-3px); }
}
@keyframes besideCurlUp {
  from { transform: scale(1); }
  to { transform: scale(.975) translateY(8px); }
}
.listen-copy {
  bottom: 66px;
  color: rgba(36,53,47,.66);
  font-size: 13px;
  letter-spacing: .08em;
  text-shadow: none;
}
.caption {
  left: 0;
  right: 0;
  z-index: 8;
  top: 510px;
  bottom: auto;
  color: var(--text-primary);
  font-family: inherit;
  font-size: 19px;
  font-weight: 600;
  line-height: 28px;
  text-align: left;
  text-shadow: none;
}
.caption::after {
  display: none;
}

.st-key-response_explanation,
.st-key-response_explanation_live {
  position: static;
  z-index: 3;
  display: block;
  width: auto;
  height: auto;
  margin: 10px 20px 8px;
  overflow: visible;
  translate: 0 67px;
  transform: none;
}
.st-key-response_explanation [data-testid="stExpander"],
.st-key-response_explanation_live [data-testid="stExpander"] {
  width: auto;
  overflow: visible;
  border: 0;
  border-radius: 0;
  background: transparent;
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
}
.st-key-response_explanation details summary,
.st-key-response_explanation_live details summary {
  display: inline-flex;
  width: auto;
  height: 34px;
  min-height: 34px;
  padding: 0;
  overflow: visible;
  border: 0;
  border-radius: 0;
  background: transparent;
  color: #5F746B;
  font-size: 15px;
  font-weight: 500;
  text-align: left;
}
.st-key-response_explanation details summary svg,
.st-key-response_explanation_live details summary svg,
.st-key-response_explanation details summary [data-testid="stIconMaterial"],
.st-key-response_explanation_live details summary [data-testid="stIconMaterial"],
.st-key-response_explanation details summary [data-testid="stExpanderToggleIcon"],
.st-key-response_explanation_live details summary [data-testid="stExpanderToggleIcon"] {
  display: none !important;
}
.st-key-response_explanation details[open],
.st-key-response_explanation_live details[open] {
  width: min(calc(100vw - 40px), 390px);
  padding: 8px 12px 12px;
  border: 1px solid rgba(36,53,47,.075);
  border-radius: 18px;
  background: rgba(255,254,250,.88);
}
.st-key-response_explanation details[open] p,
.st-key-response_explanation_live details[open] p {
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 18px;
}
.input-note {
  display: none;
}
[data-testid="stAppViewContainer"]:has(.room-shell) [data-testid="stBottomBlockContainer"] {
  background: var(--bg) !important;
}
[data-testid="stAppViewContainer"]:has(.room-shell) [data-testid="stBottom"] {
  background: var(--bg) !important;
}
[data-testid="stBottomBlockContainer"] {
  bottom: 82px !important;
  padding: 8px 20px 2px;
  background: linear-gradient(180deg, transparent, rgba(248,248,244,.96) 34%);
  pointer-events: none;
}
[data-testid="stBottomBlockContainer"] > div {
  max-width: 390px;
  margin: 0 auto;
}
[data-testid="stBottom"] {
  bottom: 82px !important;
  z-index: 900 !important;
  background: transparent !important;
  pointer-events: none;
}
[data-testid="stChatInput"] {
  min-height: 54px;
  border: 1px solid rgba(36,53,47,.10);
  border-radius: 999px;
  background: rgba(255,254,250,.94) !important;
  box-shadow: none;
  backdrop-filter: blur(8px);
  pointer-events: auto;
}
[data-testid="stChatInput"] [data-baseweb="textarea"],
[data-testid="stChatInput"] [data-baseweb="base-input"] {
  background: transparent !important;
}
[data-testid="stChatInput"] > div,
[data-testid="stChatInput"] > div > div,
[data-testid="stChatInput"] > div > div > div {
  background-color: transparent !important;
}
[data-testid="stChatInput"] * {
  border-color: transparent !important;
  outline: none !important;
  box-shadow: none !important;
}
[data-testid="stChatInput"] textarea {
  min-height: 52px !important;
  padding-top: 15px !important;
  background: transparent !important;
  color: var(--text-primary);
  font-size: 16px;
  outline: none !important;
  box-shadow: none !important;
}
[data-testid="stChatInput"] textarea::placeholder {
  color: rgba(38,58,51,.45) !important;
  opacity: 1 !important;
}
[data-testid="stChatInput"]:focus-within {
  border-color: rgba(120,153,134,.48) !important;
  box-shadow: 0 0 0 2px rgba(120,153,134,.12) !important;
}
[data-testid="stChatInputSubmitButton"] {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  margin: 5px;
  background: #789986 !important;
  color: #FFFEFA !important;
}
[data-testid="stChatInputSubmitButton"] svg {
  color: #FFFEFA !important;
  fill: #FFFEFA !important;
}

.st-key-record_foreground,
.st-key-moments_foreground {
  padding: 18px;
  border: 1px solid rgba(38,58,51,.075);
  border-radius: 19px;
  background: rgba(255,254,250,.92);
  backdrop-filter: blur(7px);
  -webkit-backdrop-filter: blur(7px);
}
.record-header,
.sticker-header {
  padding: 0 0 12px;
}
.st-key-behavior_recorder > [data-testid="stVerticalBlock"] {
  gap: 10px;
}
.st-key-behavior_observation_row [data-testid="stHorizontalBlock"] {
  align-items: start;
  gap: 10px;
}
.st-key-behavior_observation_row [data-testid="stColumn"]:first-child {
  flex: .34 1 0 !important;
}
.st-key-behavior_observation_row [data-testid="stColumn"]:last-child {
  flex: .66 1 0 !important;
}
.st-key-behavior_observation_row [data-testid="stFileUploader"] {
  position: relative;
  z-index: 2;
  width: 104px;
  height: 104px;
  min-height: 104px;
  padding: 0;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: 16px;
  background: var(--canvas-subtle);
}
.st-key-behavior_observation_row [data-testid="stFileUploaderDropzone"] {
  width: 104px;
  height: 104px;
  min-height: 104px;
  padding: 8px;
  border: 0;
  background: transparent;
}
.st-key-behavior_observation_row [data-testid="stFileUploaderDropzoneInstructions"] {
  display: none;
}
.st-key-behavior_observation_row [data-testid="stFileUploaderDropzone"] button {
  min-height: 34px;
  padding: 0 8px;
  border: 1px solid #B8C5B5;
  border-radius: 12px;
  background: var(--sage-soft);
  color: transparent;
  font-size: 0;
}
.st-key-behavior_observation_row [data-testid="stFileUploaderDropzone"] button::after {
  content: "选择照片";
  color: var(--text-primary);
  font-size: 11px;
}
.behavior-photo-label {
  min-height: 20px;
  margin-bottom: 5px;
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 500;
  line-height: 20px;
}
.st-key-behavior_observation_row [data-testid="stFileUploaderFile"],
.st-key-behavior_observation_row [data-testid="stFileUploaderFileName"],
.st-key-behavior_observation_row [data-testid="stFileUploaderFileData"] {
  display: none !important;
}
.st-key-behavior_photo_preview {
  position: relative;
  z-index: 1;
  margin-top: -104px;
  pointer-events: none;
}
.st-key-behavior_photo_preview [data-testid="stImageContainer"] img {
  width: 100% !important;
  height: 104px !important;
  border-radius: 16px;
  object-fit: cover;
}
.st-key-behavior_photo_preview .behavior-photo-image {
  display: block;
  width: 100%;
  height: 104px;
  border-radius: 16px;
  object-fit: cover;
}
.st-key-behavior_observation_row:has(.st-key-behavior_photo_preview img) [data-testid="stFileUploader"] {
  border-color: transparent;
  background: transparent;
}
.st-key-behavior_observation_row:has(.st-key-behavior_photo_preview img) [data-testid="stFileUploaderDropzone"] button {
  position: absolute;
  right: 6px;
  bottom: 6px;
  z-index: 3;
  min-height: 28px;
  padding: 0 8px;
  border-color: rgba(36,53,47,.12);
  background: rgba(255,254,250,.88);
}
.st-key-behavior_observation_row:has(.st-key-behavior_photo_preview img) [data-testid="stFileUploaderDropzone"] button::after {
  content: "更换";
  font-size: 10px;
}
.st-key-behavior_observation_row:has(.st-key-behavior_photo_preview img) .st-key-behavior_photo_preview {
  pointer-events: none;
}
.st-key-behavior_observation_row [data-testid="stTextArea"] textarea {
  min-height: 104px !important;
  max-height: 104px !important;
  border-color: var(--border);
  border-radius: 16px;
  background: rgba(255,254,250,.95);
  color: var(--text-primary);
  font-size: 14px;
  line-height: 20px;
}
.st-key-behavior_recorder [data-testid="stButton"] button[kind="secondary"],
.st-key-understand_behavior [data-testid="stButton"] button {
  min-height: 40px;
  border: 1px solid #B8C5B5;
  border-radius: 13px;
  background: var(--sage-soft);
  color: var(--text-primary);
  box-shadow: none;
}
.analysis-card {
  padding: 2px 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 20px;
}
.analysis-section {
  padding: 9px 4px;
  border-bottom: 1px solid rgba(36,53,47,.09);
}
.analysis-section:nth-child(2),
.analysis-section:nth-child(4) {
  background: linear-gradient(90deg, rgba(220,232,236,.34), rgba(234,217,219,.20), transparent 82%);
}
.analysis-section:last-child {
  border-bottom: 0;
}
.analysis-section strong {
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 500;
  line-height: 17px;
}
.analysis-section p {
  margin: 4px 0 0;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 20px;
}
.record-saved {
  padding: 12px;
  border: 1px solid rgba(36,53,47,.08);
  border-radius: 14px;
  background: var(--sage-soft);
  color: var(--text-primary);
  font-family: inherit;
}
.profile-intro,
.memory-count {
  color: var(--text-secondary);
  font-size: 11px;
}

.sticker-grid {
  gap: 12px;
  padding: 2px 0 0;
}
.sticker-card,
.sticker-card:nth-child(odd),
.sticker-card:nth-child(even) {
  padding: 6px 6px 11px;
  border: 1px solid rgba(36,53,47,.075);
  border-radius: 18px;
  background: rgba(220,232,236,.66);
  box-shadow: none;
  color: var(--text-primary);
  transform: none;
}
.sticker-card:nth-child(2n) { background: rgba(234,217,219,.68); }
.sticker-card:nth-child(3n) { background: rgba(231,237,227,.78); }
.sticker-image,
.sticker-placeholder {
  border: 0;
  border-radius: 15px;
  background: var(--surface);
}
.sticker-behavior {
  margin: 8px 5px 0;
  color: var(--text-primary);
  font-family: inherit;
  font-size: 14px;
  font-weight: 500;
  line-height: 20px;
}
.sticker-context {
  margin: 2px 5px 0;
  color: var(--text-secondary);
  font-size: 11px;
  line-height: 15px;
}
.sticker-description {
  display: -webkit-box;
  overflow: hidden;
  margin: 5px 5px 0;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 17px;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
}
.st-key-sticker_back {
  display: none;
}

@media (max-width: 640px) {
  [data-testid="stMainBlockContainer"] {
    padding: 20px 20px 148px;
  }
  .room-shell {
    height: 552px !important;
    min-height: 552px;
    border-radius: 0;
  }
  .st-key-record_foreground,
  .st-key-moments_foreground {
    padding: 16px;
  }
  .sticker-grid {
    gap: 12px;
  }
  .sticker-card {
    border-radius: 18px;
  }
}

@media (max-width: 360px) {
  [data-testid="stMainBlockContainer"] {
    padding-left: 16px;
    padding-right: 16px;
  }
  .room-shell { height: 552px !important; min-height: 552px; }
  .profile-label { font-size: 12px; }
  [class*="st-key-profile_row_"] [data-baseweb="select"] div { font-size: 12px !important; }
}
</style>
"""


def init_state() -> None:
    defaults = {
        "page": "create",
        "phase": "IDLE",
        "pet_profile": None,
        "draft_image": None,
        "draft_image_mime": None,
        "last_action": None,
        "last_response": None,
        "last_response_source": None,
        "playback_nonce": 0,
        "pet_behavior_memory": [],
        "pending_behavior_analysis": None,
        "pending_behavior_context": "",
        "pending_behavior_image_bytes": None,
        "behavior_analysis_source": None,
        "record_saved": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def streamlit_media_url(image_bytes: bytes) -> str:
    """Return an inline image URL that remains valid across Cloud reruns."""
    with Image.open(BytesIO(image_bytes)) as image:
        mime_type = Image.MIME.get(image.format, "image/jpeg")
    encoded = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


ASSETS_DIR = Path(__file__).resolve().parent / "assets"
MOTION_DIR = ASSETS_DIR / "motion"
ROOM_DIR = ASSETS_DIR / "room"
STICKER_DIR = ASSETS_DIR / "stickers"
ROOM_IDLE_PATH = ROOM_DIR / "room-idle.jpg"
EMPTY_ROOM_PATH = ROOM_DIR / "empty-room.png"
ACTION_MEDIA = {
    "idle": "idle.mp4",
    "grooming": "grooming.mp4",
    "knead": "knead.mp4",
    "come_closer": "come_closer.mp4",
    "curl_up": "curl_up.mp4",
}


def motion_video_url(action: str) -> Optional[str]:
    """Inline an available Motion Pack file; missing media stays on CSS fallback."""
    filename = ACTION_MEDIA.get(action)
    if not filename:
        return None
    path = MOTION_DIR / filename
    if not path.is_file() or path.stat().st_size == 0:
        return None
    try:
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:video/mp4;base64,{encoded}"
    except OSError:
        return None


def is_renderable_image(image_bytes: bytes) -> bool:
    """Reject truncated or mislabeled uploads before Streamlit tries to render them."""
    try:
        with Image.open(BytesIO(image_bytes)) as image:
            image.verify()
        return True
    except (UnidentifiedImageError, OSError, ValueError):
        return False


def local_image_url(path: Path) -> Optional[str]:
    """Load a project-relative image as a Cloud-safe inline URL."""
    try:
        image_bytes = path.read_bytes()
    except OSError:
        return None
    if not image_bytes or not is_renderable_image(image_bytes):
        return None
    return streamlit_media_url(image_bytes)


FRONTEND_TERM_REPLACEMENTS = {
    "emotion_response_profile": "你之前告诉我的习惯",
    "Behavioral Memory": "过去的行为记录",
    "usual_companion_behavior": "平时的陪伴方式",
    "come_closer": "靠近",
    "curl_up": "在附近窝下来",
    "grooming": "理毛",
    "knead": "踩奶",
    "anxious": "焦虑或烦躁",
    "traits": "平时的性格",
    "other": "这个动作",
    "confidence": "观察的确定程度",
}

DIARY_BEHAVIOR_COPY = {
    "come_closer": "{name}正慢慢靠近你。",
    "knead": "{name}正在轻轻踩奶。",
    "curl_up": "{name}正在附近安静地窝下来。",
    "grooming": "{name}正在认真整理自己的毛。",
    "other": "{name}正在安静地观察眼前的环境。",
}

ROOM_BEHAVIOR_COPY = {
    "come_closer": "猫咪主动靠近，有时是在寻找熟悉的接触或陪伴距离。具体代表什么，要结合当时的情境一起看。",
    "knead": "踩奶是猫咪常见的节律性动作，有时和舒适、放松或熟悉的体验有关。具体代表什么，要结合当时的情境一起看。",
    "curl_up": "猫咪在附近窝下来，有时只是想休息，也可能是在保持一个让自己舒服的陪伴距离。具体代表什么，要结合当时的情境一起看。",
    "grooming": "猫咪在紧张、环境变化，或者只是想让自己慢下来时，都可能会通过理毛来整理自己。具体代表什么，要结合当时的情境一起看。",
}


def naturalize_frontend_text(value: str) -> str:
    result = value
    for internal, natural in FRONTEND_TERM_REPLACEMENTS.items():
        result = result.replace(internal, natural)
    return result


def diary_behavior_copy(observed_behavior: str, pet_name: str) -> str:
    template = DIARY_BEHAVIOR_COPY.get(observed_behavior)
    if template:
        return template.format(name=pet_name)
    if any(character.isascii() and character.isalpha() for character in observed_behavior):
        return f"{pet_name}正在安静地观察眼前的环境。"
    natural = naturalize_frontend_text(observed_behavior).strip("。")
    return f"{pet_name}{natural}。" if pet_name not in natural else f"{natural}。"


def companion_explanation_copy(
    profile: dict,
    response: CompanionResponse,
) -> tuple[str, str]:
    pet_name = profile["name"]
    behavior_copy = ROOM_BEHAVIOR_COPY[response.action]
    emotion_key = {
        "happy": "happy",
        "sad": "sad",
        "lonely": "sad",
        "anxious": "anxious",
        "frustrated": "anxious",
        "tired": "tired",
    }.get(response.emotion)
    emotion_copy = {
        "happy": "开心",
        "sad": "难过",
        "lonely": "孤独",
        "anxious": "焦虑或烦躁",
        "frustrated": "焦虑或烦躁",
        "tired": "很累或低落",
    }.get(response.emotion, "想安静待一会")
    action_copy = {
        "come_closer": "靠近你",
        "knead": "轻轻踩奶",
        "curl_up": "在附近安静地窝下来",
        "grooming": "开始认真理毛",
    }[response.action]

    first_paragraph = []
    configured = profile.get("emotion_response_profile", {}).get(emotion_key or "")
    if configured == response.action:
        first_paragraph.append(
            f"你之前告诉我，当你{emotion_copy}的时候，{pet_name}常常会{action_copy}。"
        )

    matching_memory = next(
        (
            memory
            for memory in profile.get("pet_behavior_memory", [])
            if memory.get("observed_behavior") == response.action
        ),
        None,
    )
    if matching_memory:
        context = str(matching_memory.get("context", ""))
        if any(word in context for word in ("摸", "撸", "互动")):
            first_paragraph.append(
                f"你也曾经记录过，{pet_name}在和你互动之后，经常会有这样的习惯。"
            )
        else:
            first_paragraph.append(
                f"你也曾经记录过，{pet_name}在相似的时刻会有这样的表现。"
            )

    conclusion = {
        "come_closer": f"所以这一次，它还是用熟悉的方式靠近一点，安静地陪着你。",
        "knead": f"所以这一次，它没有急着做什么，只是在你身边轻轻踩了几下。",
        "curl_up": f"所以这一次，它选择留在附近，用自己的距离安静陪着你。",
        "grooming": f"所以这一次，它没有急着靠近你，只是用更像{pet_name}自己的方式，安静地陪着你。",
    }[response.action]
    if first_paragraph:
        about_copy = "".join(first_paragraph) + "\n\n" + conclusion
    else:
        about_copy = (
            f"{pet_name}平时更习惯用这样的方式待在你身边。"
            "随着你留下更多真实观察，我们会慢慢看见更属于它自己的小习惯。"
        )
    return behavior_copy, about_copy


def render_analysis_card(analysis: BehaviorAnalysis, pet_name: str) -> None:
    st.markdown(
        '<div class="analysis-card">'
        '<section class="analysis-section">'
        f'<strong>我看到的</strong><p>{html.escape(diary_behavior_copy(analysis.observed_behavior, pet_name))}</p>'
        '</section><section class="analysis-section">'
        f'<strong>这个动作可能在表达什么</strong><p>{html.escape(naturalize_frontend_text(analysis.general_meaning))}</p>'
        '</section><section class="analysis-section">'
        f'<strong>放回当时的情境里</strong><p>{html.escape(naturalize_frontend_text(analysis.context_interpretation))}</p>'
        '</section><section class="analysis-section">'
        f'<strong>关于{html.escape(pet_name)}</strong><p>{html.escape(naturalize_frontend_text(analysis.pet_specific_pattern))}</p>'
        '</section>'
        "</div>",
        unsafe_allow_html=True,
    )


def render_behavior_recorder(pet_name: str) -> None:
    with st.container(key="behavior_recorder"):
        if st.session_state.record_saved:
            st.markdown('<div class="record-saved">记住了。</div>', unsafe_allow_html=True)
            if st.button(
                "看看它的小动作 →",
                type="tertiary",
                use_container_width=True,
                key="saved_to_stickers",
            ):
                st.session_state.record_saved = False
                st.session_state.page = "stickers"
                st.rerun()
            if st.button("回到房间", type="tertiary", key="saved_to_room"):
                st.session_state.record_saved = False
                st.session_state.page = "room"
                st.rerun()
            return

        with st.container(key="behavior_observation_row"):
            photo_col, context_col = st.columns([.34, .66], gap="small")
            with photo_col:
                st.markdown('<div class="behavior-photo-label">照片</div>', unsafe_allow_html=True)
                observation_photo = st.file_uploader(
                    "照片",
                    type=["jpg", "jpeg", "png", "webp"],
                    key="behavior_photo",
                    label_visibility="collapsed",
                )
                if observation_photo is not None:
                    preview_bytes = bytes(observation_photo.getvalue())
                    if is_renderable_image(preview_bytes):
                        with st.container(key="behavior_photo_preview"):
                            preview_mime = observation_photo.type or "image/jpeg"
                            preview_url = (
                                f"data:{preview_mime};base64,"
                                + base64.b64encode(preview_bytes).decode("ascii")
                            )
                            st.markdown(
                                '<img class="behavior-photo-image" '
                                f'src="{html.escape(preview_url, quote=True)}" '
                                f'alt="{html.escape(pet_name)}的行为照片" />',
                                unsafe_allow_html=True,
                            )
            with context_col:
                context = st.text_area(
                    "当时发生了什么？",
                    placeholder=f"例如：我刚撸完{pet_name}，它就开始舔毛。",
                    key="behavior_context",
                    height=104,
                )
        understand = st.button(
            "帮我理解",
            key="understand_behavior",
            use_container_width=True,
        )
        use_demo = st.button("使用备用记录", key="use_demo_behavior", type="tertiary")

        if understand:
            if observation_photo is None or not context.strip():
                st.markdown(
                    '<div class="validation">请上传一张行为照片，并写下当时的情境。</div>',
                    unsafe_allow_html=True,
                )
            else:
                observation_bytes = bytes(observation_photo.getvalue())
                if not is_renderable_image(observation_bytes):
                    st.markdown(
                        '<div class="validation">这次没看清，再试一次。</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    with st.spinner("正在结合图片和情境观察…"):
                        analysis, source = analyze_behavior(
                            observation_bytes,
                            context.strip(),
                            pet_name,
                        )
                    if analysis is None:
                        st.markdown(
                            '<div class="validation">这次没看清，再试一次。</div>',
                            unsafe_allow_html=True,
                        )
                    else:
                        st.session_state.pending_behavior_analysis = analysis.model_dump()
                        st.session_state.pending_behavior_context = context.strip()
                        st.session_state.pending_behavior_image_bytes = observation_bytes
                        st.session_state.behavior_analysis_source = source

        if use_demo:
            demo = demo_grooming_analysis(pet_name)
            st.session_state.pending_behavior_analysis = demo.model_dump()
            st.session_state.pending_behavior_context = "被摸之后"
            st.session_state.pending_behavior_image_bytes = None
            st.session_state.behavior_analysis_source = "demo:grooming"

        pending = st.session_state.pending_behavior_analysis
        if pending:
            analysis = BehaviorAnalysis.model_validate(pending)
            render_analysis_card(analysis, pet_name)
            if st.button(
                "记住这次行为",
                key="confirm_behavior_memory",
                use_container_width=True,
            ):
                entry = build_memory_entry(
                    st.session_state.pending_behavior_context,
                    analysis,
                )
                pending_image = st.session_state.pending_behavior_image_bytes
                if isinstance(pending_image, (bytes, bytearray)) and pending_image:
                    entry["image_bytes"] = bytes(pending_image)
                if entry not in st.session_state.pet_behavior_memory:
                    st.session_state.pet_behavior_memory.append(entry)
                st.session_state.pending_behavior_analysis = None
                st.session_state.pending_behavior_context = ""
                st.session_state.pending_behavior_image_bytes = None
                st.session_state.record_saved = True
                st.rerun()

        count = len(st.session_state.pet_behavior_memory)
        if count:
            st.markdown(
                f'<div class="memory-count">已确认 {count} 条属于{html.escape(pet_name)}的行为记录。</div>',
                unsafe_allow_html=True,
            )


def render_response_explanation(
    slot: st.delta_generator.DeltaGenerator,
    profile: dict,
    response: CompanionResponse,
    container_key: str = "response_explanation",
) -> None:
    behavior_copy, about_copy = companion_explanation_copy(profile, response)
    with slot.container():
        with st.container(key=container_key):
            with st.expander("为什么它这样回应？ →"):
                st.markdown("**关于这个动作**")
                st.write(behavior_copy)
                st.markdown(f"**关于{profile['name']}**")
                st.write(about_copy)


def render_stage(
    profile: dict,
    phase: str = "IDLE",
    response: Optional[CompanionResponse] = None,
    playback_nonce: int = 0,
) -> str:
    profile_image_url = streamlit_media_url(profile["image"])
    idle_image_url = local_image_url(ROOM_IDLE_PATH) or profile_image_url
    action = response.action if response else "idle"
    video_url = motion_video_url(action) if response and phase == "REACTING" else None
    uses_legacy_fallback = bool(response and phase == "REACTING" and not video_url)
    room_classes = ["room-shell"]
    if video_url:
        room_classes.append("has-motion")
    if uses_legacy_fallback:
        room_classes.append("has-fallback")
    room_class = " ".join(room_classes)
    status = '<div class="listen-copy">它在听</div>' if phase == "UNDERSTANDING" else ""
    caption = ""
    if response and response.caption:
        caption = f'<div class="caption">{html.escape(response.caption)}</div>'
    motion = ""
    if video_url:
        playback_url = f"{video_url}#play={playback_nonce}"
        motion = (
            '<video class="room-media-frame motion-video" autoplay muted playsinline preload="auto" '
            'disablepictureinpicture controlslist="nodownload noplaybackrate nofullscreen" '
            f'data-playback="{playback_nonce}" '
            f'aria-label="{html.escape(profile["name"])}的动作片段">'
            f'<source src="{html.escape(playback_url, quote=True)}" type="video/mp4" />'
            "</video>"
        )
    fallback_class = f" fallback-action-{action}" if uses_legacy_fallback else ""
    return f"""
    <div class="{room_class}" aria-live="polite">
      <div class="room-media-layer">
        <img class="room-media-frame room-idle-media{fallback_class}" src="{html.escape(idle_image_url, quote=True)}" alt="{html.escape(profile['name'])}在房间里" />
        {motion}
      </div>
      {status}
      {caption}
    </div>
    """


STICKER_BEHAVIOR_LABELS = {
    "grooming": "认真理毛",
    "knead": "踩奶",
    "come_closer": "靠近",
    "curl_up": "安静窝着",
    "watching": "盯着我看",
    "other": "观察中的小动作",
}

STICKER_ASSETS = {
    "grooming": "pangpang-grooming-sticker.png",
    "watching": "pangpang-watching-sticker.png",
    "knead": "pangpang-kneading-sticker.png",
}

SHARED_BACKGROUND_ASSETS = {
    "create": EMPTY_ROOM_PATH,
    "record": EMPTY_ROOM_PATH,
    "stickers": EMPTY_ROOM_PATH,
    "moments": EMPTY_ROOM_PATH,
}


def render_shared_room_background(view: str) -> None:
    """Attach a page-scoped room backdrop without committing final visual values."""
    asset_path = SHARED_BACKGROUND_ASSETS.get(view)
    if not asset_path:
        return
    background_url = local_image_url(asset_path)
    if not background_url:
        return
    safe_view = html.escape(view, quote=True)
    st.markdown(
        f'<div class="shared-room-background shared-room-background--{safe_view}" '
        f'data-room-view="{safe_view}" aria-hidden="true">'
        f'<img src="{html.escape(background_url, quote=True)}" alt="" />'
        "</div>",
        unsafe_allow_html=True,
    )


def sticker_behavior_label(behavior: str, context: str = "") -> str:
    if behavior == "other" and any(word in context for word in ("盯", "看着", "注视")):
        return "盯着我看"
    return STICKER_BEHAVIOR_LABELS.get(behavior, "一个小动作")


def short_sticker_copy(value: str, fallback: str) -> str:
    natural = naturalize_frontend_text(value).strip()
    if not natural:
        return fallback
    first_sentence = natural.split("。", 1)[0].strip()
    if len(first_sentence) > 34:
        first_sentence = first_sentence[:34].rstrip("，、；：") + "…"
    return first_sentence + ("。" if not first_sentence.endswith("…") else "")


def sticker_image_bytes(item: dict) -> Optional[bytes]:
    for key in ("image_bytes", "image"):
        candidate = item.get(key)
        if isinstance(candidate, (bytes, bytearray)) and is_renderable_image(bytes(candidate)):
            return bytes(candidate)
        if isinstance(candidate, str):
            candidate_path = Path(candidate)
            if candidate_path.is_file():
                image_bytes = candidate_path.read_bytes()
                if is_renderable_image(image_bytes):
                    return image_bytes

    asset_name = STICKER_ASSETS.get(str(item.get("observed_behavior", "")))
    if asset_name:
        asset_path = STICKER_DIR / asset_name
        if asset_path.is_file():
            image_bytes = asset_path.read_bytes()
            if is_renderable_image(image_bytes):
                return image_bytes
    return None


def sticker_items(profile: dict) -> list[dict]:
    pet_name = profile["name"]
    real_memories = list(profile.get("pet_behavior_memory", []))
    items = [{**memory, "is_demo": False} for memory in real_memories]
    seed_items = [
        {
            "observed_behavior": "grooming",
            "context": "被撸之后",
            "pet_specific_pattern": f"{pet_name}经常会开始整理自己的毛。",
            "is_demo": True,
        },
        {
            "observed_behavior": "watching",
            "context": "我刚回到家",
            "pet_specific_pattern": f"{pet_name}有时会安静地看着我一会儿。",
            "is_demo": True,
        },
        {
            "observed_behavior": "knead",
            "context": "和我互动的时候",
            "pet_specific_pattern": f"{pet_name}会用自己的节奏踩一会儿奶。",
            "is_demo": True,
        },
    ]
    represented = {str(item.get("observed_behavior", "")) for item in items}
    for seed in seed_items:
        if len(items) >= 3:
            break
        if seed["observed_behavior"] in represented:
            continue
        items.append(seed)
        represented.add(seed["observed_behavior"])
    return items


def render_sticker_wall() -> None:
    profile = st.session_state.pet_profile
    if not profile:
        st.session_state.page = "create"
        st.rerun()

    pet_name = profile["name"]
    render_shared_room_background("stickers")
    render_main_nav("stickers")
    with st.container(key="moments_foreground"):
        st.markdown(
            '<div class="sticker-header">'
            f'<h1 class="sticker-title">{html.escape(pet_name)}的小动作</h1>'
            '<p class="sticker-subtitle">一点一点，认识它自己的方式。</p>'
            "</div>",
            unsafe_allow_html=True,
        )

        cards = []
        for item in sticker_items(profile):
            behavior = str(item.get("observed_behavior", ""))
            context = str(item.get("context", "")).strip() or "当时的一个瞬间"
            title = sticker_behavior_label(behavior, context)
            description = short_sticker_copy(
                str(item.get("pet_specific_pattern", "")),
                f"这是关于{pet_name}的一次小观察。",
            )
            image_bytes = sticker_image_bytes(item)
            if image_bytes:
                image_url = streamlit_media_url(image_bytes)
                visual = (
                    f'<img class="sticker-image" src="{html.escape(image_url, quote=True)}" '
                    f'alt="{html.escape(pet_name)}·{html.escape(title)}" />'
                )
            else:
                visual = '<div class="sticker-placeholder" aria-hidden="true"></div>'
            cards.append(
                '<article class="sticker-card">'
                f"{visual}"
                f'<div class="sticker-behavior">{html.escape(title)}</div>'
                f'<div class="sticker-context">{html.escape(context)}</div>'
                f'<div class="sticker-description">{html.escape(description)}</div>'
                "</article>"
            )
        st.markdown(
            '<section class="sticker-grid">' + "".join(cards) + "</section>",
            unsafe_allow_html=True,
        )

        with st.container(key="sticker_back"):
            if st.button("带它回房间", type="tertiary"):
                st.session_state.page = "room"
                st.rerun()


MAIN_VIEWS = (
    ("room", "房间"),
    ("record", "记录"),
    ("stickers", "小动作"),
)


def render_main_nav(active_view: str) -> None:
    with st.container(key="main_nav"):
        columns = st.columns(3)
        for column, (view, label) in zip(columns, MAIN_VIEWS):
            with column:
                if st.button(
                    label,
                    type="primary" if view == active_view else "tertiary",
                    use_container_width=True,
                    key=f"nav_{active_view}_{view}",
                ):
                    if view == "record" and active_view != "record":
                        st.session_state.record_saved = False
                    st.session_state.page = view
                    st.rerun()


def render_record_page() -> None:
    profile = st.session_state.pet_profile
    if not profile:
        reset_profile()
        st.rerun()

    st.session_state.pet_behavior_memory = profile.setdefault("pet_behavior_memory", [])
    render_shared_room_background("record")
    render_main_nav("record")
    with st.container(key="record_foreground"):
        st.markdown(
            '<div class="record-header">'
            '<h1 class="record-title">记录一个小瞬间</h1>'
            '<p class="record-subtitle">留下一次你真正观察到它的时刻。</p>'
            "</div>",
            unsafe_allow_html=True,
        )
        render_behavior_recorder(profile["name"])


def render_create_page() -> None:
    render_shared_room_background("create")
    with st.container(key="create_form"):
        st.markdown('<div class="brand-word">Beside</div>', unsafe_allow_html=True)
        st.markdown('<h1 class="create-title">认识一下它</h1>', unsafe_allow_html=True)
        st.markdown('<p class="create-copy">告诉我，它平时怎样陪着你。</p>', unsafe_allow_html=True)

        preview_slot = st.container(key="upload_preview")
        uploaded = st.file_uploader(
            "选择一张它的照片",
            type=["jpg", "jpeg", "png", "webp"],
            help="清晰、自然的生活照就很好。",
            key="cat_photo",
        )
        if uploaded is not None:
            image_bytes = bytes(uploaded.getvalue())
            if image_bytes and is_renderable_image(image_bytes):
                st.session_state.draft_image = image_bytes
                st.session_state.draft_image_mime = uploaded.type or "image/jpeg"
            else:
                st.session_state.draft_image = None
                st.session_state.draft_image_mime = None
                st.markdown(
                    '<div class="validation">这张照片无法读取，请换一张完整的 JPG、PNG 或 WEBP。</div>',
                    unsafe_allow_html=True,
                )
        if st.session_state.draft_image:
            with preview_slot:
                st.image(st.session_state.draft_image, width="stretch")

        with st.container(key="identity_row"):
            name_col, traits_col = st.columns([.68, 1.32], gap="small")
            with name_col:
                name = st.text_input("猫咪名字", placeholder="它叫什么？", max_chars=20)
            with traits_col:
                traits = st.multiselect(
                    "性格",
                    TRAITS,
                    max_selections=3,
                    placeholder="最多选择 3 个",
                )
        st.markdown('<div class="required-note">选择最像它的 1～3 个特点</div>', unsafe_allow_html=True)
        usual_behavior = st.radio(
            "它平时最常怎么陪你？",
            COMPANION_BEHAVIORS,
            index=None,
            horizontal=True,
        )

        st.markdown('<div class="profile-heading">它在你不同情绪下通常怎么回应</div>', unsafe_allow_html=True)
        emotion_response_profile = {}
        default_actions = {
            "happy": "knead",
            "sad": "come_closer",
            "anxious": "grooming",
            "tired": "curl_up",
        }
        emotion_labels = {
            "happy": "开心时",
            "sad": "难过时",
            "anxious": "焦虑 / 烦躁时",
            "tired": "累 / 低落时",
        }
        for emotion_key, _question in EMOTION_QUESTIONS:
            with st.container(key=f"profile_row_{emotion_key}"):
                accent_col, label_col, select_col, arrow_col = st.columns(
                    [.025, .39, .50, .04], gap="small"
                )
                with accent_col:
                    st.markdown('<span class="profile-accent"></span>', unsafe_allow_html=True)
                with label_col:
                    st.markdown(
                        f'<span class="profile-label">{emotion_labels[emotion_key]}</span>',
                        unsafe_allow_html=True,
                    )
                with select_col:
                    emotion_response_profile[emotion_key] = st.selectbox(
                        emotion_labels[emotion_key],
                        PROFILE_ACTIONS,
                        index=PROFILE_ACTIONS.index(default_actions[emotion_key]),
                        format_func=lambda action: PROFILE_ACTION_LABELS[action],
                        key=f"profile_{emotion_key}",
                        label_visibility="collapsed",
                    )
                with arrow_col:
                    st.markdown('<span class="profile-arrow">›</span>', unsafe_allow_html=True)

        can_submit = bool(
            st.session_state.draft_image and name.strip() and traits and usual_behavior
        )
        submitted = st.button(
            "带它回房间",
            type="primary",
            use_container_width=True,
            disabled=not can_submit,
        )
        if submitted:
            errors = []
            if not st.session_state.draft_image:
                errors.append("请先上传一张猫咪照片。")
            if not name.strip():
                errors.append("告诉我它的名字。")
            if not traits:
                errors.append("至少选择一个最像它的性格。")
            if usual_behavior is None:
                errors.append("请选择它平时最常见的陪伴方式。")
            if errors:
                st.markdown(
                    '<div class="validation">' + "<br>".join(errors) + "</div>",
                    unsafe_allow_html=True,
                )
                return
            st.session_state.pet_profile = {
                "name": name.strip(),
                "image": bytes(st.session_state.draft_image),
                "image_mime": st.session_state.draft_image_mime or "image/jpeg",
                "traits": list(traits),
                "usual_companion_behavior": usual_behavior,
                "emotion_response_profile": emotion_response_profile,
                "pet_behavior_memory": st.session_state.pet_behavior_memory,
            }
            st.session_state.page = "room"
            st.session_state.phase = "IDLE"
            st.session_state.last_action = None
            st.session_state.last_response = None
            st.rerun()


def reset_profile() -> None:
    st.session_state.page = "create"
    st.session_state.phase = "IDLE"
    st.session_state.pet_profile = None
    st.session_state.draft_image = None
    st.session_state.draft_image_mime = None
    st.session_state.last_action = None
    st.session_state.last_response = None
    st.session_state.last_response_source = None
    st.session_state.playback_nonce = 0
    st.session_state.pet_behavior_memory = []
    st.session_state.pending_behavior_analysis = None
    st.session_state.pending_behavior_context = ""
    st.session_state.pending_behavior_image_bytes = None
    st.session_state.behavior_analysis_source = None
    st.session_state.record_saved = False


def render_room_page() -> None:
    profile = st.session_state.pet_profile
    if not profile:
        reset_profile()
        st.rerun()

    if st.session_state.phase == "SETTLED":
        st.session_state.phase = "IDLE"

    render_main_nav("room")
    with st.container(key="room_top"):
        st.markdown(
            f'<div class="room-name">{html.escape(profile["name"])}</div>'
            '<div class="room-sub">它就在这里</div>',
            unsafe_allow_html=True,
        )
        if st.button("···", type="tertiary", help="重新创建"):
            reset_profile()
            st.rerun()

    stage_slot = st.empty()
    stage_slot.markdown(render_stage(profile), unsafe_allow_html=True)
    explanation_slot = st.empty()
    if st.session_state.last_response:
        render_response_explanation(
            explanation_slot,
            profile,
            CompanionResponse.model_validate(st.session_state.last_response),
        )
    st.markdown(
        '<div class="input-note">不用组织好语言，它会用自己的方式回应。</div>',
        unsafe_allow_html=True,
    )
    user_text = st.chat_input("现在想和它说什么？", key="emotion_input")

    if user_text is None:
        return
    if not user_text.strip():
        st.markdown('<div class="validation">先说一句此刻的感受吧。</div>', unsafe_allow_html=True)
        return

    st.session_state.phase = "UNDERSTANDING"
    stage_slot.markdown(
        render_stage(profile, phase="UNDERSTANDING"), unsafe_allow_html=True
    )

    response, source = get_companion_response(
        user_text=user_text.strip(),
        pet_name=profile["name"],
        traits=profile["traits"],
        usual_companion_behavior=profile["usual_companion_behavior"],
        previous_action=st.session_state.last_action,
        timeout_seconds=5.0,
        emotion_response_profile=profile.get("emotion_response_profile", {}),
        pet_behavior_memory=profile.get("pet_behavior_memory", []),
    )

    st.session_state.phase = "REACTING"
    st.session_state.last_action = response.action
    st.session_state.last_response = response.model_dump()
    st.session_state.last_response_source = source
    st.session_state.playback_nonce += 1
    stage_slot.markdown(
        render_stage(
            profile,
            phase="REACTING",
            response=response,
            playback_nonce=st.session_state.playback_nonce,
        ),
        unsafe_allow_html=True,
    )
    render_response_explanation(
        explanation_slot,
        profile,
        response,
        container_key="response_explanation_live",
    )
    st.session_state.phase = "SETTLED"


init_state()
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
st.markdown(FINAL_APPROVED_CSS, unsafe_allow_html=True)

if st.session_state.page == "room":
    render_room_page()
elif st.session_state.page == "record":
    render_record_page()
elif st.session_state.page == "stickers":
    render_sticker_wall()
else:
    render_create_page()
