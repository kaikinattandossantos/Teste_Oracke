document.addEventListener('DOMContentLoaded', () => {

    const screens = document.querySelectorAll('.screen');
    const menuItems = document.querySelectorAll('.sidebar-menu .menu-item');
    const analyzeBtn = document.getElementById('analyze-btn');
    const repoUrlInput = document.getElementById('repo-url');
    const consentCheckbox = document.getElementById('consent-checkbox');
    const repoNameSpans = document.querySelectorAll('.repo-name');
    const bugListContainer = document.getElementById('bug-list-container');
    const readmeContentContainer = document.getElementById('readme-content-container');
    const btnText = document.querySelector('.btn-text');
    const spinner = document.querySelector('.spinner');
    
    const commitBtn = document.getElementById('commit-readme-btn');
    const copyBtn = document.getElementById('copy-readme-btn');
    const prBtn = document.getElementById('pr-readme-btn');

    const modalOverlay = document.getElementById('modal-overlay');
    const modalContainer = document.getElementById('modal-container');
    const modalFilepath = document.getElementById('modal-filepath');
    const modalCodeBefore = document.getElementById('modal-code-before');
    const modalCodeAfter = document.getElementById('modal-code-after');
    const closeModalBtn = document.getElementById('close-modal-btn');
    const modalDetails = document.getElementById('modal-details');

    const codeInput = document.getElementById('code-input');
    const analyzeComplexityBtn = document.getElementById('analyze-complexity-btn');
    const complexityResultsContainer = document.getElementById('complexity-results-container');
    const complexityOverall = document.getElementById('complexity-overall');
    const complexityBottlenecks = document.getElementById('complexity-bottlenecks');
    const complexitySuggestions = document.getElementById('complexity-suggestions');


    let fullReadmeContent = '';
    let currentRepoUrl = '';
    let analysisHasBeenPerformed = false;


    async function fetchAnalysisFromBackend(repoUrl) {
        const response = await fetch("http://localhost:5000/analyze", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ repo_url: repoUrl })
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || "Erro desconhecido ao gerar o README");
        }
        const data = await response.json();
        return { 
            bugs: data.bugs || [], 
            readme: data.readme || "README.md vazio gerado pela IA."
        };
    }

    async function commitReadmeToGithub(repoUrl, readmeContent) {
        const response = await fetch("http://localhost:5000/commit", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ 
                repo_url: repoUrl,
                readme_content: readmeContent
            })
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || "Erro desconhecido ao fazer o commit");
        }
        return await response.json();
    }


    function showScreen(screenId) {
        screens.forEach(screen => screen.classList.add('hidden'));
        const screenToShow = document.getElementById(screenId);
        if (screenToShow) screenToShow.classList.remove('hidden');
    }

    async function typeReadme(textToType) {
        readmeContentContainer.innerHTML = '';
        let currentText = '';
        for (let i = 0; i < textToType.length; i++) {
            currentText += textToType[i];
            readmeContentContainer.innerHTML = marked.parse(currentText) + '<span class="typing-cursor"></span>';
            await new Promise(resolve => setTimeout(resolve, 5));
        }
        readmeContentContainer.innerHTML = marked.parse(textToType);
    }

    function populateBugList(bugs) {
        bugListContainer.innerHTML = '';
        if (!bugs || bugs.length === 0) {
            bugListContainer.innerHTML = '<div class="empty-state"><i class="fas fa-check-circle"></i><p>Nenhum problema crítico encontrado na análise inicial!</p></div>';
            return;
        }

    consentCheckbox.addEventListener('change', () => {
        analyzeBtn.disabled = !consentCheckbox.checked;
    });

    analyzeBtn.addEventListener('click', async () => {
        const repoUrl = repoUrlInput.value;
        if (!repoUrl) {
            alert('Por favor, insira a URL de um repositório.');
            return;
        }

        btnText.classList.add('hidden');
        spinner.classList.remove('hidden');
        analyzeBtn.disabled = true;

        try {
            const analysisData = await fetchAnalysisFromBackend(repoUrl);
            fullReadmeContent = analysisData.readme;
            currentRepoUrl = repoUrl;
            analysisHasBeenPerformed = true;

            const repoName = repoUrl.split('/').slice(-2).join('/').replace('.git', '');
            repoNameSpans.forEach(span => span.textContent = repoName);

            populateBugList(analysisData.bugs);
            showScreen('readme-screen'); 
            await typeReadme(analysisData.readme);
            
            menuItems.forEach(i => i.classList.remove('active'));
            document.querySelector('.menu-item[data-target="readme-screen"]').classList.add('active');

        } catch (error) {
            alert(`Erro ao analisar o repositório: ${error.message}`);
        } finally {
            btnText.classList.remove('hidden');
            spinner.classList.add('hidden');
            analyzeBtn.disabled = !consentCheckbox.checked;
        }
    });

    menuItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const target = item.getAttribute('data-target');
            if (target === 'input-screen' || target === 'complexity-screen') {
                showScreen(target);
                menuItems.forEach(i => i.classList.remove('active'));
                item.classList.add('active');
            } else if (analysisHasBeenPerformed) {
                showScreen(target);
                menuItems.forEach(i => i.classList.remove('active'));
                item.classList.add('active');
            } else {
                alert("Primeiro, analise um repositório para poder navegar.");
            }
        });
    });

    copyBtn.addEventListener('click', () => {
        navigator.clipboard.writeText(fullReadmeContent).then(() => alert('Conteúdo do README copiado!'));
    });

    commitBtn.addEventListener('click', async () => {
        if (!currentRepoUrl || !fullReadmeContent) return;
        const originalText = commitBtn.innerHTML;
        commitBtn.innerHTML = '<span class="spinner-btn"></span> Comitando...';
        commitBtn.disabled = true;
        try {
            const result = await commitReadmeToGithub(currentRepoUrl, fullReadmeContent);
            alert(result.message);
            if (result.url) window.open(result.url, '_blank');
        } catch (error) {
            alert(`Erro: ${error.message}`);
        } finally {
            commitBtn.innerHTML = originalText;
            commitBtn.disabled = false;
        }
    });

    prBtn.addEventListener('click', () => {
        alert("FUNCIONALIDADE FUTURA: Criar um Pull Request com o novo README.md.");
    });
    
    analyzeComplexityBtn.addEventListener('click', () => {
        alert("FUNCIONALIDADE FUTURA: A análise de complexidade será integrada com a IA.");
    });


    showScreen('input-screen');
});
