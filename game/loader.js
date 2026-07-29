(() => {
  'use strict';
  const parts = ['parts/game-00.part.txt', 'parts/game-01.part.txt', 'parts/game-02.part.txt', 'parts/game-03.part.txt', 'parts/game-04.part.txt', 'parts/game-05.part.txt', 'parts/game-06.part.txt', 'parts/game-07.part.txt', 'parts/game-08.part.txt'];
  const reportFailure = (error) => {
    console.error(error);
    const target = document.getElementById('test-report') || document.body;
    target.classList?.remove('hidden');
    target.textContent = `游戏代码加载失败：${error.message}`;
  };
  Promise.all(parts.map(async (part) => {
    const response = await fetch(part);
    if (!response.ok) throw new Error(`${part} (${response.status})`);
    return response.text();
  }))
    .then((chunks) => {
      const blob = new Blob([chunks.join('\n')], { type: 'text/javascript' });
      const script = document.createElement('script');
      script.src = URL.createObjectURL(blob);
      script.addEventListener('load', () => URL.revokeObjectURL(script.src), { once: true });
      script.addEventListener('error', () => reportFailure(new Error('无法执行游戏代码')), { once: true });
      document.body.appendChild(script);
    })
    .catch(reportFailure);
})();
