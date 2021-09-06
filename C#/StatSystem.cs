using System.Collections.ObjectModel;
using System.Collections.Generic;
using UnityEngine;

namespace Sourcery.Stats
{
    [System.Serializable]
    public abstract class StatSystem : MonoBehaviour
    {
        protected List<Relation> relations;
        public ReadOnlyCollection<Relation> Relations { get; protected set; }


        protected virtual void Start()
        {
            relations = new List<Relation>();
            Relations = new ReadOnlyCollection<Relation>(relations);
        }
    }
}