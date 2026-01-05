"use client";

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  PlayIcon,
  PauseIcon,
  SpeakerWaveIcon,
  ChevronDownIcon,
} from "@heroicons/react/24/solid";
import type { Match, Moment, Persona, CommentaryResponse } from "@/types";
import * as api from "@/lib/api";

export default function Home() {
  // State
  const [matches, setMatches] = useState<Match[]>([]);
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [selectedMatch, setSelectedMatch] = useState<Match | null>(null);
  const [selectedPersona, setSelectedPersona] = useState<Persona | null>(null);
  const [moments, setMoments] = useState<Moment[]>([]);
  const [selectedMoment, setSelectedMoment] = useState<Moment | null>(null);
  const [commentary, setCommentary] = useState<CommentaryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [showMatchDropdown, setShowMatchDropdown] = useState(false);
  const [selectedLanguage, setSelectedLanguage] = useState<"en" | "hi">("en");

  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Cache for generated commentary: key = "matchId-ballNumber-personaId"
  const commentaryCache = useRef<Map<string, CommentaryResponse>>(new Map());

  // Helper to get cache key (includes language)
  const getCacheKey = (
    matchId: string,
    ballNumber: string,
    personaId: string,
    language: string,
  ) => `${matchId}-${ballNumber}-${personaId}-${language}`;

  // Load initial data
  useEffect(() => {
    async function loadData() {
      try {
        const [matchesData, personasData] = await Promise.all([
          api.fetchMatches(),
          api.fetchPersonas(),
        ]);
        setMatches(matchesData);
        setPersonas(personasData);
        if (personasData.length > 0) {
          setSelectedPersona(personasData[0]);
        }
      } catch (err) {
        console.error("Failed to load data:", err);
      }
    }
    loadData();
  }, []);

  // Load moments when match changes
  useEffect(() => {
    if (!selectedMatch) return;
    async function loadMoments() {
      try {
        const momentsData = await api.fetchMoments(selectedMatch!.id);
        setMoments(momentsData);
        setSelectedMoment(null);
        setCommentary(null);
      } catch (err) {
        console.error("Failed to load moments:", err);
      }
    }
    loadMoments();
  }, [selectedMatch]);

  // Play audio helper
  const playAudio = (audioBase64: string) => {
    if (audioRef.current) {
      audioRef.current.src = `data:audio/mp3;base64,${audioBase64}`;
      audioRef.current.play();
      setIsPlaying(true);
    }
  };

  // Generate or retrieve cached commentary
  async function handleGenerateCommentary(
    matchId?: string,
    ballNumber?: string,
    personaId?: string,
    language?: "en" | "hi",
  ) {
    const m = matchId || selectedMatch?.id;
    const b = ballNumber || selectedMoment?.ball_number;
    const p = personaId || selectedPersona?.id;
    const lang = language || selectedLanguage;

    if (!m || !b || !p) return;

    const cacheKey = getCacheKey(m, b, p, lang);

    // Check cache first
    const cached = commentaryCache.current.get(cacheKey);
    if (cached) {
      setCommentary(cached);
      if (cached.audio_base64) {
        playAudio(cached.audio_base64);
      }
      return;
    }

    // Generate new commentary
    setIsLoading(true);
    setCommentary(null);

    try {
      const result = await api.generateCommentary(m, b, p, lang);

      // Cache the result
      commentaryCache.current.set(cacheKey, result);
      setCommentary(result);

      if (result.audio_base64) {
        playAudio(result.audio_base64);
      }
    } catch (err) {
      console.error("Failed to generate commentary:", err);
    } finally {
      setIsLoading(false);
    }
  }

  // Get gradient class for current persona
  const gradientClass = selectedPersona
    ? `gradient-${selectedPersona.id}`
    : "gradient-benaud";

  return (
    <div
      className={`min-h-screen ${gradientClass} transition-all duration-1000`}
    >
      {/* Hidden audio element */}
      <audio
        ref={audioRef}
        onEnded={() => setIsPlaying(false)}
        onPause={() => setIsPlaying(false)}
        onPlay={() => setIsPlaying(true)}
      />

      {/* Header */}
      <header className="border-b border-white/10">
        <div className="container mx-auto px-6 py-8">
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center"
          >
            <h1 className="text-5xl md:text-7xl font-bold tracking-tight">
              <span
                className="font-doshi"
                style={{ color: selectedPersona?.color || "#F5F5DC" }}
              >
                सूक्ष्म वाचक
              </span>
            </h1>
            <p className="mt-2 text-lg text-white/60 tracking-widest uppercase">
              The Subtle Commentator
            </p>
          </motion.div>
        </div>
      </header>

      <main className="container mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Left Panel - Controls */}
          <div className="lg:col-span-4 space-y-6">
            {/* Match Selector */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              className="glass rounded-2xl p-6"
            >
              <h2 className="text-sm uppercase tracking-widest text-white/40 mb-4">
                Select Match
              </h2>
              <div className="relative">
                <button
                  onClick={() => setShowMatchDropdown(!showMatchDropdown)}
                  className="w-full flex items-center justify-between p-4 bg-white/5 rounded-xl border border-white/10 hover:border-white/20 transition-colors"
                >
                  <span className="text-white/80">
                    {selectedMatch
                      ? `${selectedMatch.teams[0]} vs ${selectedMatch.teams[1]}`
                      : "Choose a match..."}
                  </span>
                  <ChevronDownIcon className="w-5 h-5 text-white/40" />
                </button>

                <AnimatePresence>
                  {showMatchDropdown && (
                    <motion.div
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -10 }}
                      className="absolute z-10 w-full mt-2 bg-zinc-900 rounded-xl border border-white/10 shadow-2xl max-h-64 overflow-y-auto"
                    >
                      {matches.map((match) => (
                        <button
                          key={match.id}
                          onClick={() => {
                            setSelectedMatch(match);
                            setShowMatchDropdown(false);
                          }}
                          className="w-full text-left p-4 hover:bg-white/5 transition-colors border-b border-white/5 last:border-0"
                        >
                          <div className="font-medium text-white/90">
                            {match.teams[0]} vs {match.teams[1]}
                          </div>
                          <div className="text-sm text-white/40 mt-1">
                            {match.venue} • {match.date}
                          </div>
                        </button>
                      ))}
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </motion.div>

            {/* Persona Selector */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.1 }}
              className="glass rounded-2xl p-6"
            >
              <h2 className="text-sm uppercase tracking-widest text-white/40 mb-4">
                Choose Your Voice
              </h2>
              <div className="space-y-3">
                {personas.map((persona) => (
                  <motion.button
                    key={persona.id}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => {
                      setSelectedPersona(persona);
                      // Auto-play if a moment is already selected (uses cache if available)
                      if (selectedMoment && selectedMatch) {
                        handleGenerateCommentary(
                          selectedMatch.id,
                          selectedMoment.ball_number,
                          persona.id,
                        );
                      }
                    }}
                    className={`persona-card w-full p-4 rounded-xl text-left transition-all ${
                      selectedPersona?.id === persona.id
                        ? "selected bg-white/10"
                        : "bg-white/5 hover:bg-white/8"
                    }`}
                    style={{
                      borderColor:
                        selectedPersona?.id === persona.id
                          ? persona.color
                          : "transparent",
                      color: persona.color,
                    }}
                  >
                    <div className="flex items-center gap-4">
                      <div
                        className="w-12 h-12 rounded-full flex items-center justify-center text-xl font-bold"
                        style={{ backgroundColor: `${persona.color}20` }}
                      >
                        {persona.name.charAt(0)}
                      </div>
                      <div>
                        <div
                          className="font-semibold"
                          style={{ color: persona.color }}
                        >
                          {persona.name}
                        </div>
                        <div className="text-sm text-white/50">
                          {persona.tagline}
                        </div>
                      </div>
                    </div>
                  </motion.button>
                ))}
              </div>
            </motion.div>

            {/* Language Selector */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.15 }}
              className="glass rounded-2xl p-6"
            >
              <h2 className="text-sm uppercase tracking-widest text-white/40 mb-4">
                Language
              </h2>
              <div className="flex gap-3">
                <button
                  onClick={() => {
                    setSelectedLanguage("en");
                    if (selectedMoment && selectedMatch && selectedPersona) {
                      handleGenerateCommentary(
                        selectedMatch.id,
                        selectedMoment.ball_number,
                        selectedPersona.id,
                        "en",
                      );
                    }
                  }}
                  className={`flex-1 py-3 px-4 rounded-xl font-medium transition-all ${
                    selectedLanguage === "en"
                      ? "bg-white/20 text-white border-2 border-white/30"
                      : "bg-white/5 text-white/60 border-2 border-transparent hover:bg-white/10"
                  }`}
                >
                  English
                </button>
                <button
                  onClick={() => {
                    setSelectedLanguage("hi");
                    if (selectedMoment && selectedMatch && selectedPersona) {
                      handleGenerateCommentary(
                        selectedMatch.id,
                        selectedMoment.ball_number,
                        selectedPersona.id,
                        "hi",
                      );
                    }
                  }}
                  className={`flex-1 py-3 px-4 rounded-xl font-medium transition-all ${
                    selectedLanguage === "hi"
                      ? "bg-white/20 text-white border-2 border-white/30"
                      : "bg-white/5 text-white/60 border-2 border-transparent hover:bg-white/10"
                  }`}
                >
                  हिंदी
                </button>
              </div>
            </motion.div>

            {/* Key Moments */}
            {selectedMatch && (
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.2 }}
                className="glass rounded-2xl p-6"
              >
                <h2 className="text-sm uppercase tracking-widest text-white/40 mb-4">
                  Key Moments ({moments.length})
                </h2>
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {moments.map((moment) => (
                    <motion.button
                      key={moment.id}
                      whileHover={{ x: 4 }}
                      onClick={() => {
                        setSelectedMoment(moment);
                        setCommentary(null);
                      }}
                      className={`moment-card w-full p-3 rounded-lg text-left ${
                        moment.is_wicket
                          ? "wicket"
                          : moment.event_type === "boundary_six"
                          ? "six"
                          : "four"
                      } ${selectedMoment?.id === moment.id ? "selected" : ""}`}
                    >
                      <div className="flex justify-between items-start">
                        <div>
                          <div className="text-sm font-medium text-white/90">
                            {moment.description}
                          </div>
                          <div className="text-xs text-white/40 mt-1">
                            Over {moment.ball_number} • {moment.score}
                          </div>
                        </div>
                        <span
                          className={`text-xs px-2 py-1 rounded-full ${
                            moment.is_wicket
                              ? "bg-red-500/20 text-red-400"
                              : moment.event_type === "boundary_six"
                              ? "bg-yellow-500/20 text-yellow-400"
                              : "bg-green-500/20 text-green-400"
                          }`}
                        >
                          {moment.is_wicket
                            ? "W"
                            : moment.event_type === "boundary_six"
                            ? "6"
                            : "4"}
                        </span>
                      </div>
                    </motion.button>
                  ))}
                </div>
              </motion.div>
            )}
          </div>

          {/* Right Panel - Commentary Display */}
          <div className="lg:col-span-8">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="glass rounded-3xl p-8 min-h-[500px] flex flex-col"
            >
              {/* Commentary Area */}
              <div className="flex-1 flex items-center justify-center">
                <AnimatePresence mode="wait">
                  {isLoading ? (
                    <motion.div
                      key="loading"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="text-center"
                    >
                      <div
                        className="spinner mx-auto"
                        style={{ borderTopColor: selectedPersona?.color }}
                      />
                      <p className="mt-4 text-white/40">
                        Generating commentary...
                      </p>
                    </motion.div>
                  ) : commentary ? (
                    <motion.div
                      key="commentary"
                      initial={{ opacity: 0, scale: 0.95 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 0.95 }}
                      className="text-center w-full"
                    >
                      <p
                        className={`commentary-text ${selectedPersona?.id} animate-fade-in-up`}
                        style={{ color: selectedPersona?.color }}
                      >
                        "{commentary.text}"
                      </p>

                      {/* Audio Controls */}
                      {commentary.audio_base64 && (
                        <motion.div
                          initial={{ opacity: 0, y: 20 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: 0.3 }}
                          className="mt-8 flex items-center justify-center gap-4"
                        >
                          <button
                            onClick={() => {
                              if (audioRef.current) {
                                if (isPlaying) {
                                  audioRef.current.pause();
                                } else {
                                  audioRef.current.play();
                                }
                              }
                            }}
                            className="w-16 h-16 rounded-full flex items-center justify-center transition-all"
                            style={{
                              backgroundColor: `${selectedPersona?.color}20`,
                              border: `2px solid ${selectedPersona?.color}40`,
                            }}
                          >
                            {isPlaying ? (
                              <PauseIcon
                                className="w-8 h-8"
                                style={{ color: selectedPersona?.color }}
                              />
                            ) : (
                              <PlayIcon
                                className="w-8 h-8"
                                style={{ color: selectedPersona?.color }}
                              />
                            )}
                          </button>

                          {/* Waveform Animation */}
                          <div
                            className="waveform"
                            style={{ color: selectedPersona?.color }}
                          >
                            {[...Array(8)].map((_, i) => (
                              <div
                                key={i}
                                className={`waveform-bar ${
                                  isPlaying ? "playing" : ""
                                }`}
                                style={{
                                  height: isPlaying ? undefined : "20%",
                                  animationDelay: `${i * 0.05}s`,
                                }}
                              />
                            ))}
                          </div>

                          <div className="text-sm text-white/40">
                            {commentary.duration_seconds.toFixed(1)}s
                          </div>
                        </motion.div>
                      )}
                    </motion.div>
                  ) : selectedMoment ? (
                    <motion.div
                      key="generate"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="text-center"
                    >
                      <p className="text-white/60 mb-6">
                        {selectedMoment.description}
                      </p>
                      <motion.button
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        onClick={() => handleGenerateCommentary()}
                        className="px-8 py-4 rounded-full font-semibold transition-all"
                        style={{
                          backgroundColor: selectedPersona?.color,
                          color: "#0a0a0a",
                        }}
                      >
                        <SpeakerWaveIcon className="w-5 h-5 inline mr-2" />
                        Generate Commentary
                      </motion.button>
                    </motion.div>
                  ) : (
                    <motion.div
                      key="empty"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="text-center"
                    >
                      <div className="text-6xl mb-6">🏏</div>
                      <p className="text-white/40 text-lg">
                        Select a match and a key moment to hear the commentary
                      </p>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              {/* Persona Attribution */}
              {commentary && selectedPersona && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.5 }}
                  className="mt-8 pt-6 border-t border-white/10 flex items-center justify-between"
                >
                  <div className="flex items-center gap-3">
                    <div
                      className="w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold"
                      style={{
                        backgroundColor: `${selectedPersona.color}20`,
                        color: selectedPersona.color,
                      }}
                    >
                      {selectedPersona.name.charAt(0)}
                    </div>
                    <div>
                      <div
                        className="font-medium"
                        style={{ color: selectedPersona.color }}
                      >
                        {selectedPersona.name}
                      </div>
                      <div className="text-xs text-white/40">
                        {selectedPersona.style} • {selectedPersona.accent}
                      </div>
                    </div>
                  </div>
                  <div className="text-xs text-white/30">Powered by AI</div>
                </motion.div>
              )}
            </motion.div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-white/10 mt-12">
        <div className="container mx-auto px-6 py-6 text-center text-white/30 text-sm">
          <p>सूक्ष्म वाचक • The Subtle Commentator</p>
          <p className="mt-1">
            AI-powered cricket commentary in the style of legends
          </p>
        </div>
      </footer>
    </div>
  );
}
