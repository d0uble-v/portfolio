using System;
using System.Collections.Generic;
using UnityEngine;

namespace Sourcery.Stats
{
    [Serializable]
    public abstract class Relation
    {
        protected StatSystem statSystem;

        public Relation(StatSystem statSystem)
        {
            this.statSystem = statSystem;
        }
    }
}