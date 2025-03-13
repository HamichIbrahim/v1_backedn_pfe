from langchain import LLMChain 
from langchain.prompts import FewShotPromptTemplate, PromptTemplate
from langchain import LLMChain 
from langchain.prompts import FewShotPromptTemplate, PromptTemplate
schema_description = """
use just the nodes and properties and relations that existe in this Database Schema:
Node properties:
- **Daira**
  - `nom_francais`: STRING Example: "Aoulef"
  - `nom_arabe`: STRING Example: "أولف"
- **Commune**
  - `longitude`: FLOAT Min: -1.3565692, Max: 8.1994276
  - `nom_francais`: STRING Example: "Aoulef"
  - `latitude`: FLOAT Min: 0, Max: 36.839681
  - `nom_arabe`: STRING Example: "أولف"
- **Wilaya**
  - `nom_francais`: STRING Example: "Adrar"
  - `nom_arabe`: STRING Example: "ادرار"
  - `matricule`: INTEGER Min: 1, Max: 58/// used lik this  matricule:44
- **Unite**
  - `nom_francais`: STRING Example: "Brigade territoriale de la GN Aoulef"
  - `Type`: STRING Available options: ['Brigade']
  - `nom_arabe`: STRING Example: "الفرقة الإقليمية للدرك الوطني بأولف"
- **Affaire**
  - `Number`: STRING Example: "Drog_1"
  - `date`: STRING Example: "17-04-2023"
  - `Type`: STRING Available options: ['مخدرات']
- **Personne**
  - `birth_date`: STRING Example: "22-09-1994"
  - `national_id`: STRING Example: "45339030376158"
  - `firstname`: STRING Example: "موهوب"
  - `num`: INTEGER Example: "1"
  - `lastname`: STRING Example: "منير"
- **Virtuel**
  - `Nom`: STRING Example: "Michael Morales"
  - `Type`: STRING Example: "Facebook"
  - `ID`: STRING Example: "175575809826100"
- **Phone**
  - `operateur`: STRING Example: "Djezzy"
  - `num`: STRING Example: "0792803473"
Relationship properties:
- **appartient**
  - `identity: INTEGER` Min: 0, Max:  632
- **situer**
  - `identity: INTEGER` Min: 633, Max:  1090
- **Traiter**
  - `identity: INTEGER` Min: 1091, Max:  4090
- **Impliquer**
  - `identity: INTEGER` Min: 4091, Max:  13209
- **Proprietaire**
  - `identity: INTEGER` Example: "13210"
- **Appel_telephone**
  - `identity: INTEGER` Min: 44734, Max:  54356
  - `duree_sec: INTEGER` Min: 11, Max:  115
The relationships:
(:Daira)-[:appartient]-(:Wilaya)
(:Commune)-[:appartient]-(:Daira)
(:Unite)-[:situer]-(:Commune)
(:Affaire)-[:Impliquer]-(:Personne)
(:Affaire)-[:Traiter]-(:Unite)
(:Personne)-[:Appel_telephone]-(:Affaire)
(:Virtuel)-[:Proprietaire]-(:Personne)
(:Phone)-[:Proprietaire]-(:Personne)
(:Phone)-[:Appel_telephone]-(:Phone)
"""

# Define the example template to format examples as "Question: ... Entities: ... Answer: ..."
example_prompt = PromptTemplate(
    input_variables=["question", "query"],
    template="Question: {question}\nquery: {query}"
)
examples = []


examples = [
    # Direct Relations
    {
        "question": "ما هي القضايا التي تعالجها الوحدة المسماة 'الفرقة الإقليمية'؟",
        "query": "MATCH (u:Unit {{arabic_name: 'الفرقة الإقليمية'}})-[:Handles]-(a:Affaire) RETURN a,u"
    },
    {
        "question": "ما هي الدوائر التي تنتمي إلى ولاية وهران؟",
        "query": "MATCH (d:Daira)-[:belongs_to]-(s:State {{arabic_name: 'وهران'}}) RETURN d,s"
    },
    {
        "question": "ما هي أرقام الهواتف التي يمتلكها الشخص الذي يحمل رقم التعريف الوطني 55163071427360؟",
        "query": "MATCH (p:Person)-[:Owner]-(ph:Phone) WHERE p.nationel_id = '55163071427360' RETURN ph,p"
    },
    {
        "question": "ما هي جميع المكالمات التي تمت من رقم الهاتف 0771234567؟",
        "query": "MATCH (ph1:Phone {{num: '0771234567'}})-[ph_call:Phone_Call]-(ph2:Phone) RETURN ph2,ph1"
    },
    {
        "question": "ما هي القضايا المرتبطة بالشخص نجلاء قنون؟",
        "query": "MATCH (p:Person {{firstname: 'نجلاء', lastname: 'قنون'}})-[:Involves]-(a:Affaire) RETURN a,p"
    },
    {
        "question": "ما هي جميع الأشخاص المتورطين في قضية Drog_19؟",
        "query": "MATCH (p:Person)-[:Involves]-(a:Affaire {{Number: 'Drog_19'}}) RETURN p,a"
    },
    {
        "question": "ما هي جميع الأشخاص الذين ولدوا في عام 1990؟",
        "query": "MATCH (p:Person) WHERE p.birth_date CONTAINS '1990' RETURN p"
    },
    {
        "question": "ما هي جميع القضايا التي تحتوي على كلمة 'سرقة' في نوعها؟",
        "query": "MATCH (a:Affaire) WHERE a.Type CONTAINS 'سرقة' RETURN a"
    },
    # Added from your original examples (corrected)
    {
        "question": "ماهي أنواع القضايا التي تتعامل معها الوحدة 5؟",
        "query": "MATCH (u:Unit {{nom_arabe: 'الوحدة 5'}})-[:Traiter]-(a:Affaire) RETURN DISTINCT a,u"
    },

    # Negative
    {
        "question": "من هم الأشخاص المعنيين بالقضايا الذين لا يملكون أي حسابات افتراضية؟",
        "query": "MATCH (p:Person)-[:Involves]-(a:Affaire) WHERE NOT EXISTS {{ MATCH (v:Virtual)-[:Owner]-(p) }} RETURN p"
    },
    {
        "question": "من هم الأشخاص الذين ليسوا متورطين في قضية المخدرات ولكن على اتصال بأشخاص متورطين؟",
        "query": """
        MATCH (p1:Person)-[:Involves]-(a:Affaire {{Type: 'مخدرات'}})
        MATCH (p1)-[:Owner]-(ph1:Phone)
        MATCH (ph1)-[:Phone_Call]-(ph2:Phone)
        MATCH (ph2)-[:Owner]-(p2:Person)
        WHERE NOT (p2)-[:Involves]-(:Affaire {{Type: 'مخدرات'}})
        RETURN DISTINCT p2
        """
    },
    # Added from your original examples (corrected)
    {
        "question": "ماهي الأرقام التي لم تجرِ مكالمات مع الرقم 0666123456؟",
        "query": """
        MATCH (ph1:Phone)
        WHERE NOT EXISTS {{
            MATCH (ph1)-[:Appel_telephone]-(ph2:Phone {{num: '0666123456'}})
        }}
        RETURN ph1
        """
    },
    {
        "question": "ماهي الوحدات التي لا تتعامل مع قضايا التهريب؟",
        "query": """
        MATCH (u:Unit)
        OPTIONAL MATCH (u)-[:Traiter]-(a:Affaire {{Type: 'تهريب'}})
        WITH u, COUNT(a) AS nb
        WHERE nb = 0
        RETURN u
        """
    },

    # Aggregation
    {
        "question": "ما هو متوسط مدة المكالمات الهاتفية لكل شخص؟",
        "query": """
        MATCH (p:Person)-[:Owner]-(ph:Phone)-[ph_call:Phone_Call]-()
        RETURN p, AVG(ph_call.duration_second) AS متوسط_المدة
        """
    },
    {
        "question": "من هم الأشخاص الذين تورطوا في أكثر من قضية؟",
        "query": """
        MATCH (p:Person)-[:Involves]-(a:Affaire)
        WITH p, COUNT(a) AS case_count
        WHERE case_count > 1
        RETURN p
        """
    },
    {
        "question": "كم عدد القضايا التي تتعامل معها كل وحدة؟",
        "query": """
        MATCH (u:Unit)-[:Handles]-(a:Affaire)
        RETURN u AS Unit, COUNT(a) AS CaseCount
        """
    },
    {
        "question": "ما هو متوسط عدد القضايا لكل بلدية؟",
        "query": """
        MATCH (co:Commune)-[:located_in]-(u:Unit)-[:Handles]-(a:Affaire)
        WITH co, COUNT(a) AS CaseCount
        RETURN AVG(CaseCount) AS AverageCasesPerCommune
        """
    },
    {
        "question": "كم عدد الأشخاص المتورطين في قضايا المخدرات؟",
        "query": """
        MATCH (a:Affaire {{Type: 'مخدرات'}})-[:Involves]-(p:Person)
        RETURN COUNT(DISTINCT p) AS DrugCasePersons
        """
    },
    {
        "question": "كم عدد القضايا التي وقعت في كل ولاية؟",
        "query": """
        MATCH (s:State)-[:belongs_to]-(d:Daira)-[:belongs_to]-(co:Commune)-[:located_in]-(u:Unit)-[:Handles]-(a:Affaire)
        RETURN s AS State, COUNT(a) AS CaseCount
        """
    },
    {
        "question": "ما هي جميع الهواتف التي يمتلكها أشخاص ولدوا بين تاريخ 1980-01-01 و1985-01-01؟",
        "query": "MATCH (p:Person)-[:Owner]-(ph:Phone) WHERE p.birth_date >= '1980-01-01' AND p.birth_date <= '1985-12-31' RETURN ph"
    },
    # Added from your original examples (corrected)
    {
        "question": "كم عدد الحسابات الافتراضية لكل نوع؟",
        "query": """
        MATCH (v:Virtuel)-[:Proprietaire]-(p:Person)
        WITH v.Type AS Type_Compte, COUNT(v) AS Nombre_de_Comptes
        RETURN Type_Compte, Nombre_de_Comptes
        ORDER BY Type_Compte
        """
    },
    {
        "question": "ما هو عدد الأشخاص المتورطين لكل قضية؟",
        "query": """
        MATCH (p:Person)-[:Impliquer]-(a:Affaire)
        WITH a, COUNT(p) AS PersonCount
        RETURN a, PersonCount
        """
    },

    # Indirect Relations
    {
        "question": "من هم الأشخاص الذين تورطوا في قضايا بلدية الجزائر؟",
        "query": """
        MATCH (u:Unit)-[:located_in]-(:Commune {{french_name: 'الجزائر'}})
        MATCH (p:Person)-[:Involves]-(a:Affaire)-[:Handles]-(u)
        RETURN p
        """
    },
    {
        "question": "ما هي الولايات الخمس الأكثر تعرضًا للقضايا؟",
        "query": """
        MATCH (a:Affaire)-[:Handles]-(u:Unit)-[:located_in]-(co:Commune)-[:belongs_to]-(d:Daira)-[:belongs_to]-(s:State)
        RETURN s.arabic_name, COUNT(a) AS عدد_القضايا
        ORDER BY عدد_القضايا DESC
        LIMIT 5
        """
    },
    {
        "question": "ما هي البلديات الخمس الأكثر تعرضًا للقضايا؟",
        "query": """
        MATCH (a:Affaire)-[:Handles]-(u:Unit)-[:located_in]-(co:Commune)
        RETURN co.arabic_name, COUNT(a) AS عدد_القضايا
        ORDER BY عدد_القضايا DESC
        LIMIT 5
        """
    },
    {
        "question": "ماهي القضايا التي تتعامل معها ولاية Alger؟",
        "query": """
        MATCH (s:State {{french_name: 'Alger'}})-[:belongs_to]-(d:Daira)-[:belongs_to]-(co:Commune)-[:located_in]-(u:Unit)-[:Handles]-(a:Affaire)
        RETURN a
        """
    },
    {
        "question": "ماهي القضايا التي تورط فيها أشخاص على اتصال بالرقم 0654464646؟",
        "query": """
        MATCH (ph:Phone {{num: '0654464646'}})-[:Owner]-(p:Person)-[:Involves]-(a:Affaire)
        RETURN a
        """
    },
   

    # Complex
    {
        "question": "من هم الأشخاص المتورطين في قضايا متعددة الأنواع؟",
        "query": """
        MATCH (p:Person)-[:Involves]-(a:Affaire)
        WITH p, COUNT(DISTINCT a.Type) AS type_count
        WHERE type_count > 1
        RETURN p
        """
    },
    {
        "question": "من هم الأشخاص الذين لديهم أكثر من رقم هاتف ومتورطين في قضايا؟",
        "query": """
        MATCH (p:Person)-[:Owner]-(ph:Phone)
        MATCH (p)-[:Involves]-(a:Affaire)
        WITH p, COUNT(ph) AS phone_count
        WHERE phone_count > 1
        RETURN p
        """
    },
    # Added from your original examples (corrected)
    {
        "question": "من هم الأشخاص الذين لديهم مكالمات تزيد مدتها عن 300 ثانية ومتورطين في قضايا؟",
        "query": """
        MATCH (p:Person)-[:Owner]-(ph1:Phone)-[rel:Appel_telephone]-(ph2:Phone)
        WHERE rel.duree_sec > 300
        MATCH (p)-[:Impliquer]-(a:Affaire)
        RETURN DISTINCT p
        """
    },

    # Path
    {
        "question": "ما هي العلاقات بين بلدية الجزائر الفرقة الإقليمية للدرك الوطني بأولف؟",
        "query": """
        MATCH (co:Commune {{arabic_name: 'الجزائر'}}) 
        MATCH (u:Unit {{arabic_name: 'الفرقة الإقليمية للدرك الوطني بأولف'}})
        MATCH path = (co)-[*..8]-(u)
        RETURN path
        """
    },
    {
        "question": "ما هي العلاقات بين شخص بن علي محمد وحساب افتراضي ID user123؟",
        "query": """
        MATCH (p:Person {{firstname: 'محمد', lastname: 'بن علي'}})
        MATCH (v:Virtual {{ID: 'user123'}})
        MATCH path = (p)-[*..8]-(v)
        RETURN path
        """
    },
    # Added from your original examples (corrected)
    {
        "question": "ما هي العلاقات بين الشخص أحمد بن محمد والوحدة الفرقة الإقليمية للدرك الوطني بأولف",
        "query": """
        MATCH (p:Person {{firstname: 'محمد', lastname: 'بن علي'}})
        MATCH (u:Unit {{nom_arabe: 'الفرقة الإقليمية للدرك الوطني بأولف"'}})
        MATCH path = (p)-[*..8]-(u)
        RETURN path
        """
    }
]

# Mapping table for nodes and properties
mapping_table = {
    # Node mappings
    "Personne": "Person",
    "Daira": "Daira",
    "Commune": "Commune",
    "Wilaya": "State",
    "Unite": "Unit",
    "Affaire": "Case",
    "Virtuel": "Virtual",
    "Phone": "Phone",
    
    # Property mappings
    "nom_arabe": "arabic_name",
    "nom_francais": "french_name",
    "matricule": "code",
    "Type": "Type",
    "Number": "Number",
    "date": "date",
    "num": "num",
    "ID": "ID",
    "Nom": "Name",
    "operateur": "operator",
    
    # Relationship mappings
    "appartient": "belongs_to",
    "situer": "located_in",
    "Traiter": "Handles",
    "Impliquer": "Involves",
    "Proprietaire": "Owner",
    "Appel_telephone": "Phone_Call",
    
    # Relationship property mappings
    "duree_sec": "duration_seconds"
}


def generate_cypher_queries(mapping_table, query):
    """
    Replaces keys in the query with their corresponding values from the mapping table.
    
    Args:
        mapping_table (dict): A dictionary mapping real schema names to the first schema names.
        query (str): The Cypher query to be updated.
    
    Returns:
        str: The updated Cypher query.
    """
    # Iterate over the mapping table and replace keys in the query
    for real_name, old_name in mapping_table.items():
        query = query.replace(old_name, real_name)
    return query

def update_exemples(mapping_table, exemples):
    """
    Updates the `query` field in each dictionary of the `exemples` list using the `generate_cypher_queries` function.
    
    Args:
        mapping_table (dict): A dictionary mapping real schema names to the first schema names.
        exemples (list): A list of dictionaries, each containing a `question` and `query`.
    
    Returns:
        list: The updated `exemples` list.
    """
    # Iterate over each example in the list
    for example in exemples:
        # Update the query using the mapping table
        example["query"] = generate_cypher_queries(mapping_table, example["query"])
    return exemples
examples = update_exemples(mapping_table, examples)
print(examples)

from langchain import LLMChain
from langchain.prompts import FewShotPromptTemplate, PromptTemplate
from langchain_community.vectorstores import Neo4jVector
from langchain_core.example_selectors import SemanticSimilarityExampleSelector
from langchain_community.embeddings import HuggingFaceEmbeddings

# Neo4j connection details
neo4j_url = "bolt://localhost:7687"
neo4j_user = "neo4j"
neo4j_password = "12345678"

arabic_embedder = HuggingFaceEmbeddings(
    model_name="aubmindlab/bert-base-arabertv02",
    model_kwargs={'device': 'cpu'}
)

example_selector = SemanticSimilarityExampleSelector.from_examples(
    examples,
    arabic_embedder,
    Neo4jVector,
    url=neo4j_url,
    username=neo4j_user,
    password=neo4j_password,
    k=3,
    input_keys=["question"],
)