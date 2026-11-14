export default function LandingPage() {
  return (
    <>
      <div id="bg"></div>
      <canvas id="fx" aria-hidden="true"></canvas>
      <svg width="0" height="0" style={{ position: "absolute" }} aria-hidden="true">
        <symbol id="sat" viewBox="0 0 120 60">
          <g stroke="#BFE3F5" strokeWidth="1.2">
            <rect x="2" y="18" width="42" height="24" fill="#2E7FC4" />
            <rect x="76" y="18" width="42" height="24" fill="#2E7FC4" />
            <path d="M16 18v24M30 18v24M90 18v24M104 18v24M2 30h42M76 30h42" fill="none" />
          </g>
          <rect x="46" y="14" width="28" height="32" rx="4" fill="#E8F0EA" />
          <rect x="46" y="26" width="28" height="8" fill="#F0C36B" />
          <path d="M60 14V4M52 4h16" stroke="#E8F0EA" strokeWidth="2" />
        </symbol>
      </svg>

      <div className="brand l">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" strokeWidth="2.2" strokeLinecap="round">
          <path d="M12 22V9" />
          <path d="M12 13c-5 0-7-3-7-7 5 0 7 2 7 7z" />
          <path d="M12 11c0-4 2-6 7-6 0 4-2 6-7 6z" />
        </svg>
        <span>OUTWEATHER</span>
      </div>
      <div className="brand r">Alicante · Kansas demo</div>
      <nav className="dots" id="dots" aria-label="Scene navigation">
        <div className="dot a"></div>
        <div className="dot"></div>
        <div className="dot"></div>
        <div className="dot"></div>
        <div className="dot"></div>
        <div className="dot"></div>
        <div className="dot"></div>
      </nav>
      <div className="hud" aria-live="off">
        <small id="hl">Altitude</small>
        <b id="hv">36,000 km</b>
      </div>
      <button className="top" id="top" aria-label="Back to top">
        ↑
      </button>

      <div className="stage">
        {/* PROBLEM 1 · The hook */}
        <section className="scene on" id="s0">
          <div className="copy">
            <p className="kick">The problem · Alicante, Spain</p>
            <h1 className="t">They sow knowing they won&apos;t harvest.</h1>
            <p className="sub">
              Climate change already causes million-euro crop losses in Alicante: cherry down 63%, cereal down 30%, citrus
              hit by disease. Farmers keep sowing just to keep aid — every year, a single blind bet.
            </p>
          </div>
          <div className="pl p1 par" data-s="520"></div>
          <div className="pl p2 par" data-s="380"></div>
          <div className="pl p3 par" data-s="260"></div>
          <div className="pl p4 par" data-s="200"></div>
          <div className="cue">
            <span>Scroll to descend</span>
            <b>⌄</b>
          </div>
        </section>

        {/* PROBLEM 2 · The core issue */}
        <section className="scene" id="s1">
          <div className="copy">
            <p className="kick w">The core issue</p>
            <h1 className="t">Rain, heat and frost decide the harvest.</h1>
            <p className="sub">
              A farmer chooses what to plant, not what the weather will do. Every planting decision is, today, a single bet.
            </p>
          </div>
          <div className="earth" id="earth">
            <canvas id="earth-canvas"></canvas>
            <div className="earth-shading"></div>
          </div>
        </section>

        {/* PROBLEM 3 · Water */}
        <section className="scene" id="s2">
          <div className="copy">
            <p className="kick">The water problem</p>
            <h1 className="t">Next year&apos;s water is unknown.</h1>
            <p className="sub">
              Nobody in the Vega Baja knows how much water 2027 will bring. The Tajo–Segura transfer delivered 562.6 hm³ in
              2025–26, and in May 2026 a Supreme Court ruling cleared the way for changes to it.
            </p>
          </div>
          <div className="limb" id="limb"></div>
          <svg className="sat par" data-s="700" style={{ left: "12%", top: "34%" }} viewBox="0 0 120 60">
            <use href="#sat" />
          </svg>
          <svg
            className="sat par"
            data-s="460"
            style={{ right: "14%", top: "46%", animationDelay: "-2s" }}
            viewBox="0 0 120 60"
          >
            <use href="#sat" />
          </svg>
          <svg
            className="sat par"
            data-s="300"
            style={{ left: "40%", top: "30%", width: 60, height: 30, opacity: 0.7 }}
            viewBox="0 0 120 60"
          >
            <use href="#sat" />
          </svg>
          <div className="cols" id="cols">
            <div className="card">
              <h3>
                <i style={{ background: "var(--rs-water)" }}></i>Water
              </h3>
              <p>Test irrigation schedules and find where peak-month demand can come down.</p>
            </div>
            <div className="card">
              <h3>
                <i style={{ background: "#DE7B3C" }}></i>Climate
              </h3>
              <p>Check frost, heat and rainfall risk for each crop, shown as ✓, !, ▲ or ✖.</p>
            </div>
            <div className="card">
              <h3>
                <i style={{ background: "var(--rs-accent)" }}></i>Rotation
              </h3>
              <p>Alternate cereals, legumes and fallow to build soil and credit nitrogen.</p>
            </div>
          </div>
        </section>

        {/* PROBLEM 4 · Losses already on the ground */}
        <section className="scene" id="s3">
          <div className="copy">
            <p className="kick w">Losses on the ground</p>
            <h1 className="t">Losses are already piling up.</h1>
            <p className="sub">Across Alicante, the damage shows in the fields and in the cellars.</p>
          </div>
          <div className="cl par" data-s="1500" style={{ left: "4%", top: "62%", scale: "1.5" }}></div>
          <div className="cl par" data-s="1100" style={{ right: "2%", top: "70%", scale: "1.2" }}></div>
          <div className="cl par" data-s="800" style={{ left: "34%", top: "52%", scale: "0.9" }}></div>
          <div className="plane" id="plane" aria-hidden="true">
            <div className="trail"></div>
            <svg viewBox="0 0 240 80" fill="none">
              <path
                d="M120 34L96 12H117L152 32Z"
                fill="#D7E4F0"
                stroke="#9FB6CE"
                strokeWidth="1.2"
                strokeLinejoin="round"
              />
              <path
                d="M36 44L10 55H32L62 48Z"
                fill="#BFD3E6"
                stroke="#9FB6CE"
                strokeWidth="1.2"
                strokeLinejoin="round"
              />
              <path
                d="M26 30L14 5H40L70 28Z"
                fill="#4E9A4A"
                stroke="#2F5E33"
                strokeWidth="1.2"
                strokeLinejoin="round"
              />
              <path
                d="M24 30C24 28 28 27 32 27H196C218 27 236 36 240 42C236 48 218 55 196 55H48C32 55 24 50 24 44Z"
                fill="#fff"
                stroke="#9FB6CE"
                strokeWidth="1.5"
              />
              <path d="M46 47H200" stroke="#7BC96F" strokeWidth="3" strokeLinecap="round" />
              <g fill="#4FA3D1">
                <circle cx="70" cy="37" r="2.4" />
                <circle cx="82" cy="37" r="2.4" />
                <circle cx="94" cy="37" r="2.4" />
                <circle cx="106" cy="37" r="2.4" />
                <circle cx="118" cy="37" r="2.4" />
                <circle cx="130" cy="37" r="2.4" />
                <circle cx="142" cy="37" r="2.4" />
                <circle cx="154" cy="37" r="2.4" />
                <circle cx="166" cy="37" r="2.4" />
                <circle cx="178" cy="37" r="2.4" />
              </g>
              <path d="M204 34L224 38L212 41Z" fill="#2E7FC4" />
              <ellipse cx="124" cy="62" rx="16" ry="7" fill="#7F9BB8" stroke="#5F7C9A" strokeWidth="1" />
              <path
                d="M112 46L72 77H100L156 48Z"
                fill="#CFE0EF"
                stroke="#9FB6CE"
                strokeWidth="1.2"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <div className="cl par" data-s="1300" style={{ left: "58%", top: "84%", scale: "1.7" }}></div>
          <div className="cl par" data-s="600" style={{ left: "8%", top: "40%", scale: "0.7", opacity: 0.7 }}></div>
          <div className="cl par" data-s="500" style={{ right: "12%", top: "38%", scale: "0.6", opacity: 0.6 }}></div>
        </section>

        {/* PROBLEM 5 · The repeated bet (dark) */}
        <section className="scene dk" id="s4">
          <div className="copy">
            <div className="swap">
              <div className="cp" id="cpA">
                <p className="kick">The bet</p>
                <h1 className="t">One crop. One plan. One bet.</h1>
                <p className="sub">Farmers plant based on last season&apos;s results, then wait to see what the weather brings.</p>
              </div>
              <div className="cp" id="cpB">
                <p className="kick">Repeated shocks</p>
                <h1 className="t">The same risk, season after season.</h1>
                <p className="sub">
                  Drought, heat and frost keep coming back. Without a tested plan, one bad year can cost the harvest and
                  weaken the field for the next.
                </p>
              </div>
            </div>
          </div>
          <div className="bgl">
            <img className="par" data-s="120" src="/255.jpg" alt="Farmland illustration" />
          </div>
          <div className="rot" id="rot">
            <div className="frame" id="frame"></div>
            <div className="plot g1" id="pl0">
              <div className="chip">
                <svg viewBox="0 0 48 48" fill="none" stroke="#0B0F0C" strokeWidth="2.5" strokeLinecap="round">
                  <path d="M24 44V8" />
                  <path d="M24 14c-6 0-8-4-8-8 6 0 8 3 8 8zM24 14c6 0 8-4 8-8-6 0-8 3-8 8zM24 24c-6 0-8-4-8-8 6 0 8 3 8 8zM24 24c6 0 8-4 8-8-6 0-8 3-8 8z" />
                </svg>
              </div>
            </div>
            <div className="plot g2" id="pl1">
              <div className="chip">
                <svg viewBox="0 0 48 48" fill="none" stroke="#0B0F0C" strokeWidth="2.5" strokeLinecap="round">
                  <path d="M24 44V22" />
                  <path d="M24 24c-10 0-14-6-14-14 10 0 14 6 14 14zM24 24c10 0 14-6 14-14-10 0-14 6-14 14z" />
                </svg>
              </div>
            </div>
            <div className="plot g3" id="pl2">
              <div className="chip">
                <svg viewBox="0 0 48 48" fill="none" stroke="#0B0F0C" strokeWidth="2.5" strokeLinecap="round">
                  <circle cx="24" cy="18" r="7" />
                  <path d="M24 25v19M24 4v4M11 18h4M33 18h4M15 9l3 3M33 9l-3 3M15 27l3-3M33 27l-3-3" />
                </svg>
              </div>
            </div>
            <div className="plot g4" id="pl3">
              <div className="chip">
                <svg viewBox="0 0 48 48" fill="none" stroke="#0B0F0C" strokeWidth="2.5" strokeLinecap="round">
                  <path d="M6 32h36M10 24h28M14 16h20M6 40h36" />
                </svg>
              </div>
            </div>
            <div className="status">
              <i id="stDot"></i>
              <span id="stTxt">Year 1 · Drought test</span>
            </div>
          </div>
        </section>

        {/* PROBLEM 6 · Soil and water */}
        <section className="scene" id="s5">
          <div className="bgl">
            <div className="speck par" data-s="80"></div>
            <svg className="par" data-s="140" viewBox="0 0 1600 900" preserveAspectRatio="xMidYMid slice">
              <path
                d="M0 250Q300 210 600 255T1200 240T1600 260V420Q1200 400 800 430T0 410Z"
                fill="#4A3523"
                opacity=".7"
              />
              <path d="M0 430Q300 400 700 440T1600 430V620Q1100 590 700 630T0 610Z" fill="#7D5A3C" opacity=".5" />
              <path d="M0 640Q400 610 800 650T1600 640V780Q1000 760 600 790T0 780Z" fill="#B08968" opacity=".35" />
              <path d="M0 800Q500 780 900 810T1600 800V900H0Z" fill="#5F5B55" opacity=".7" />
              <g fill="#6B5A4A">
                <ellipse cx="180" cy="520" rx="26" ry="17" />
                <ellipse cx="1380" cy="330" rx="34" ry="20" />
                <ellipse cx="1220" cy="700" rx="22" ry="14" />
                <ellipse cx="320" cy="720" rx="30" ry="18" />
                <ellipse cx="90" cy="350" rx="16" ry="10" />
                <ellipse cx="1500" cy="560" rx="24" ry="15" />
              </g>
              <g stroke="#DCC7AE" strokeWidth="2" fill="none" opacity=".3" strokeLinecap="round">
                <path d="M120 150C150 260 90 330 140 460" />
                <path d="M1480 140C1440 250 1500 340 1450 470" />
                <path d="M300 160c30 90-20 170 20 260" />
                <path d="M1300 150c-20 100 30 170-10 270" />
                <path d="M140 300c-40 20-60 50-80 90M1450 300c40 20 70 40 90 90" />
              </g>
            </svg>
            <div className="aq"></div>
          </div>
          <div className="copy">
            <p className="kick">Below the surface</p>
            <h1 className="t">Soil and water pay the price.</h1>
            <p className="sub">
              Each soil layer decides how much water a crop can reach. When rain fails, shallow roots run dry first.
            </p>
          </div>
          <div className="soil" id="soil">
            <svg
              viewBox="100 0 560 400"
              fill="none"
              fontFamily="Inter,sans-serif"
              fontSize="13"
              fontWeight="600"
            >
              <rect x="120" y="60" width="320" height="50" fill="#2C2016" />
              <rect x="120" y="110" width="320" height="75" fill="#4A3523" />
              <rect x="120" y="185" width="320" height="95" fill="#7D5A3C" />
              <rect x="120" y="280" width="320" height="70" fill="#B08968" />
              <rect x="120" y="350" width="320" height="40" fill="#5F5B55" />
              <rect x="120" y="52" width="320" height="10" rx="5" fill="#4E9A4A" />
              <text x="456" y="90">0–15 cm · Topsoil</text>
              <text x="456" y="152">15–40 cm · Horizon A</text>
              <text x="456" y="236">40–90 cm · Clay (B)</text>
              <text x="456" y="320">90–150 cm · Horizon C</text>
              <text x="456" y="374">Bedrock</text>
              <path d="M280 52V30" stroke="#4E9A4A" strokeWidth="5" strokeLinecap="round" />
              <path
                d="M280 40C255 40 244 26 244 8 266 8 280 20 280 40zM280 34C280 16 292 6 312 6 312 24 300 34 280 34z"
                fill="#7BC96F"
              />
              <path
                d="M280 62V150M280 90C255 100 240 120 232 150M280 90C305 100 322 120 330 150M280 125C268 142 262 160 260 182M280 125C294 142 300 160 304 182"
                stroke="#B9E3AE"
                strokeWidth="2.5"
                strokeLinecap="round"
                opacity=".85"
              />
              <g className="drop">
                <path d="M170 66c-6 9-10 14-10 19a10 10 0 0020 0c0-5-4-10-10-19z" fill="#4FA3D1" />
              </g>
              <g className="drop" style={{ animationDelay: "-1.6s" }}>
                <path d="M390 66c-6 9-10 14-10 19a10 10 0 0020 0c0-5-4-10-10-19z" fill="#4FA3D1" />
              </g>
            </svg>
          </div>
        </section>

        {/* SOLUTION (final) */}
        <section className="scene" id="s6">
          <div className="bgl">
            <div className="end-glow glow-1"></div>
            <div className="end-glow glow-2"></div>
            <div className="end-glow glow-3"></div>
          </div>
          <div className="end" id="end">
            <p className="tag">Outweather</p>
            <h2>It&apos;s not about predicting, it&apos;s about protecting.</h2>
            <p className="sol">
              In Alicante, farmers have sown knowing they wouldn&apos;t harvest. Before putting a single seed into the
              soil, Outweather simulates what future their field can endure against past droughts and 2050 climate
              scenarios, built on open NASA satellite data.
            </p>
            <a className="cta" href="/app" id="cta">
              Open the tool <span aria-hidden="true">→</span>
            </a>
          </div>
          <p className="disc">
            Outweather is an open simulation tool based on NASA Earth observation data. It is not affiliated with, or
            endorsed by, NASA, USDA or the University of Alicante.
          </p>
        </section>
      </div>
      <div className="track"></div>
    </>
  );
}
